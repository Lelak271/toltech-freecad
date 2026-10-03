"""
Toltech point and edge picker for FreeCAD.

This module is responsible for:gui

1. Activating a one-shot selection in FreeCAD.
2. Detecting the next left mouse click.
3. Validating the selected entity.
4. Converting the selection into Toltech data.
5. Sending the selected entity to Toltech.App.
6. Sending user-friendly hints to Toltech.App when the
   selected entity is not compatible with the requested selection.
"""

import json
import threading
import urllib.request

import FreeCAD
import FreeCADGui 


# ============================================================================
# Configuration
# ============================================================================

# Base URL of the HTTP server hosted by Toltech.App.
#
# FreeCAD -> Toltech
#
# Port 5123.
TOLTECH_BASE_URL = "http://127.0.0.1:5123"


# ============================================================================
# Picker
# ============================================================================

class ToltechPicker:
    """
    Handles one-shot geometric selection in the FreeCAD 3D view.

    Currently supported:

        - Point
        - Edge
    """

    def __init__(self):
        """
        Initializes the picker.
        """

        # Active FreeCAD 3D view.
        self.view = None

        # Identifier returned by FreeCAD when
        # the mouse callback is registered.
        self.callback_id = None

        # Current selection mode.
        #
        # Possible values:
        #
        #   "point"
        #   "edge"
        self.selection_type = None

    # ========================================================================
    # Point
    # ========================================================================

    def pick_point(self):
        """
        Activates one-shot point selection.

        The next left mouse click in the 3D view
        is converted into a 3D point.
        """

        if not self._start_selection("point"):
            return

        FreeCAD.Console.PrintMessage(
            "Toltech: click a point in the 3D view.\n"
        )

    # ========================================================================
    # Edge
    # ========================================================================

    def pick_edge(self):
        """
        Activates one-shot edge selection.

        The next left mouse click in the 3D view
        must correspond to an edge.
        """

        if not self._start_selection("edge"):
            return

        FreeCAD.Console.PrintMessage(
            "Toltech: click an edge in the 3D view.\n"
        )

    # ========================================================================
    # Common selection initialization
    # ========================================================================

    def _start_selection(self, selection_type):
        """
        Initializes a one-shot mouse selection.

        Parameters
        ----------
        selection_type:
            "point" or "edge".

        Returns
        -------
        bool
            True if the selection mode was successfully started.
        """

        # A FreeCAD document must be open.
        if FreeCAD.ActiveDocument is None:

            FreeCAD.Console.PrintError(
                "Toltech: no active FreeCAD document.\n"
            )

            return False

        # Get the active 3D view.
        self.view = (
            FreeCADGui.ActiveDocument.ActiveView
        )

        # Remove a possible previous callback.
        self.stop()

        # Store the requested selection type.
        self.selection_type = selection_type

        # Register the common mouse callback.
        self.callback_id = (
            self.view.addEventCallback(
                "SoMouseButtonEvent",
                self._on_mouse_event
            )
        )

        return True

    # ========================================================================
    # Mouse event
    # ========================================================================

    def _on_mouse_event(self, event):
        """
        Handles the next mouse click in the FreeCAD 3D view.
        """

        # Only process the left mouse button.
        if event.get("Button") != "BUTTON1":
            return

        # Only process the button-down event.
        if event.get("State") != "DOWN":
            return

        try:

            # Get the 2D mouse position.
            position = event.get("Position")

               # Debug: display exactly what FreeCAD gives us.
            FreeCAD.Console.PrintMessage(
                "Toltech EVENT:\n"
                + str(event)
                + "\n")

            FreeCAD.Console.PrintMessage(
                "Toltech POSITION:\n"
                + str(position)
                + "\n"
        )


            # Process according to the requested
            # selection type.
            if self.selection_type == "point":

                self._handle_point(position)

            elif self.selection_type == "edge":

                self._handle_edge(position)

        except Exception as error:

            # A real technical error stops the selection.
            self.stop()

            FreeCAD.Console.PrintError(
                "Toltech: selection failed: "
                + str(error)
                + "\n"
            )

    # ========================================================================
    # Point handling
    # ========================================================================
    def _handle_point(self, position):
        """
        Identifies the exact 3D point on the object surface
        located under the mouse cursor.
        """
        if position is None:
            FreeCAD.Console.PrintWarning(
                "Toltech: no mouse position received.\n"
            )
            return

        # Pick against the actual geometry under the cursor,
        # not a virtual plane at focal distance.
        info = self.view.getObjectInfo(position)

        # Nothing was found under the mouse.
        if info is None:
            FreeCAD.Console.PrintMessage(
                "Toltech: no point found at this position.\n"
            )
            self._send_hint_async(
                "Aucun point trouvé à cet endroit. Cliquez sur une pièce."
            )
            return

        # Coordinates of the picked point on the surface.
        x = info.get("x")
        y = info.get("y")
        z = info.get("z")

        if x is None or y is None or z is None:
            FreeCAD.Console.PrintMessage(
                "Toltech: no 3D coordinates in pick result.\n"
            )
            self._send_hint_async(
                "Impossible de déterminer les coordonnées à cet endroit."
            )
            return

        point = FreeCAD.Vector(x, y, z)

        FreeCAD.Console.PrintMessage(
            "Toltech: 3D point: "
            f"X={point.x}, "
            f"Y={point.y}, "
            f"Z={point.z}\n"
        )

        # Selection is one-shot.
        self.stop()

        # Send the resulting 3D point asynchronously,
        # to avoid blocking the FreeCAD UI thread.
        self._send_point_async(point)
  
    # ========================================================================
    # Edge handling
    # ========================================================================

    def _handle_edge(self, position):
        """
        Identifies the FreeCAD edge (or axis) located under
        the mouse cursor and computes its direction vector,
        expressed in the document's global reference frame —
        consistent with the coordinate frame used for points.

        Accepted entities:
            - A real edge of a solid/sketch (EdgeXX)
            - A datum axis or origin axis, which FreeCAD also
              exposes as an EdgeXX sub-element

        Rejected entities:
            - A point on a surface (FaceXX)
            - A vertex (VertexXX)
        """
        # Ask FreeCAD which object is under the cursor.
        info = self.view.getObjectInfo(position)

        # Nothing was found under the mouse.
        if info is None:
            self._send_hint_async(
                "Aucune entité sélectionnée. "
                "Veuillez cliquer sur une arête ou un axe."
            )
            return

        # Name of the selected FreeCAD object.
        object_name = info.get("Object")

        # Name of the selected sub-element.
        #
        # Examples:
        #
        #   Edge1   (arête d'une pièce, ou axe)
        #   Face1   (point sur une surface -> exclu)
        #   Vertex1 (exclu)
        sub_element = info.get("Component")

        # We only accept EdgeXX (covers both real edges
        # and axes, since FreeCAD represents axes as edges).
        if not sub_element or not sub_element.startswith("Edge"):
            # IMPORTANT :
            # We do not stop the selection.
            #
            # The user can immediately try again.
            self._send_hint_async(
                "Cette sélection n'est pas une arête ni un axe. "
                "Veuillez cliquer sur une arête ou un axe."
            )
            return

        # Retrieve the FreeCAD object.
        document_object = FreeCAD.ActiveDocument.getObject(object_name)

        if document_object is None:
            self._send_hint_async(
                "Impossible de récupérer l'entité sélectionnée. "
                "Veuillez sélectionner une autre arête ou un axe."
            )
            return

        # Retrieve the actual edge geometry.
        try:
            edge_shape = document_object.Shape.getElement(sub_element)
        except Exception:
            self._send_hint_async(
                "Impossible de récupérer la géométrie de cette entité."
            )
            return

        direction_vector = self._compute_edge_direction(edge_shape)

        if direction_vector is None:
            self._send_hint_async(
                "La direction de cette entité est indéfinie."
            )
            return

        # The selection is now valid.
        self.stop()

        # Direction expressed in the document's global
        # reference frame (same frame as for points).
        payload = {
            "u": float(direction_vector.x),
            "v": float(direction_vector.y),
            "w": float(direction_vector.z)
        }

        self._send_edge_async(payload)

    def _compute_edge_direction(self, edge_shape):
        """
        Computes the direction vector of an edge (or axis),
        in the document's global reference frame.

        Uses the exact geometric direction for straight lines
        (edges and axes are both straight lines in FreeCAD),
        and falls back to the vertex-to-vertex vector for any
        other edge type (arcs, splines, ...).

        Returns None if no valid direction can be determined.
        """
        curve = getattr(edge_shape, "Curve", None)

        # Straight line (covers both real edges and axes):
        # use the exact geometric direction.
        if curve is not None and curve.__class__.__name__ in (
            "Line",
            "LineSegment"
        ):
            direction_vector = FreeCAD.Vector(curve.Direction)

            if direction_vector.Length == 0:
                return None

            direction_vector.normalize()
            return direction_vector

        # Any other edge type: fall back to vertex-to-vertex.
        if len(edge_shape.Vertexes) < 2:
            return None

        start = edge_shape.Vertexes[0].Point
        end = edge_shape.Vertexes[-1].Point

        direction_vector = end - start

        if direction_vector.Length == 0:
            return None

        direction_vector.normalize()
        return direction_vector

    # ========================================================================
    # HTTP - Point
    # ========================================================================

    def _send_point_async(self, point):
        """
        Sends the point in a background thread.
        """

        thread = threading.Thread(
            target=self._send_point,
            args=(point,),
            daemon=True
        )

        thread.start()

    def _send_point(self, point):
        """
        Sends the selected point to Toltech.App.
        """

        payload = {
            "x": float(point.x),
            "y": float(point.y),
            "z": float(point.z)
        }

        self._send_json(
            "/api/cad/point",
            payload
        )

    # ========================================================================
    # HTTP - Edge
    # ========================================================================

    def _send_edge_async(self, payload):
        """
        Sends the edge in a background thread.
        """

        thread = threading.Thread(
            target=self._send_edge,
            args=(payload,),
            daemon=True
        )

        thread.start()

    def _send_edge(self, payload):
        """
        Sends the selected edge to Toltech.App.
        """

        self._send_json(
            "/api/cad/edge",
            payload
        )

    # ========================================================================
    # HTTP - Hint
    # ========================================================================

    def _send_hint_async(self, message):
        """
        Sends a user-facing hint to Toltech.App
        without stopping the current selection.
        """

        thread = threading.Thread(
            target=self._send_hint,
            args=(message,),
            daemon=True
        )

        thread.start()

    def _send_hint(self, message):
        """
        Sends a user-facing hint to Toltech.App.

        This message is not considered an error.
        Therefore, nothing is written to the FreeCAD console
        when the request succeeds.
        """

        self._send_json(
            "/api/cad/hint",
            {
                "message": message
            },
            log_success=False
        )

    # ========================================================================
    # Generic HTTP sender
    # ========================================================================

    def _send_json(
        self,
        endpoint,
        payload,
        log_success=True
    ):
        """
        Sends a JSON POST request to Toltech.App.

        Parameters
        ----------
        endpoint:
            HTTP endpoint.

        payload:
            Dictionary serialized as JSON.

        log_success:
            Indicates whether a successful request should
            be displayed in the FreeCAD console.
        """

        url = (
            TOLTECH_BASE_URL
            + endpoint
        )

        # Serialize the payload.
        data = json.dumps(
            payload
        ).encode("utf-8")

        # Build the HTTP request.
        request = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:

            # Send the request.
            with urllib.request.urlopen(
                request,
                timeout=2
            ) as response:

                # Check HTTP status.
                if (
                    response.status < 200
                    or response.status >= 300
                ):
                    raise RuntimeError(
                        "Toltech returned HTTP "
                        + str(response.status)
                    )

            # Only log successful operations when requested.
            if log_success:

                FreeCAD.Console.PrintMessage(
                    "Toltech: selection sent successfully.\n"
                )

        except Exception as error:

            # A communication error is different from
            # an invalid user selection.
            FreeCAD.Console.PrintError(
                "Toltech: unable to communicate "
                "with Toltech: "
                + str(error)
                + "\n"
            )

    # ========================================================================
    # Stop
    # ========================================================================

    def stop(self):
        """
        Stops the current one-shot selection.
        """

        if (
            self.view is not None
            and self.callback_id is not None
        ):

            try:

                self.view.removeEventCallback(
                    "SoMouseButtonEvent",
                    self.callback_id
                )

            except Exception:
                pass

        # Clear the callback.
        self.callback_id = None

        # Clear the selection mode.
        self.selection_type = None


# ============================================================================
# Shared picker instance
# ============================================================================

# One picker instance is shared by the entire
# Toltech FreeCAD module.
_picker = ToltechPicker()


def get_picker():
    """
    Returns the shared ToltechPicker instance.
    """

    return _picker