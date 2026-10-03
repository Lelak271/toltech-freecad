"""
Local HTTP server used by Toltech to communicate with FreeCAD.

Endpoints:

    POST /api/cad/pick-point

This endpoint is called by Toltech.App.

It activates point selection in FreeCAD.

After the user clicks a point, ToltechPicker.py sends
the selected point to:

    POST http://127.0.0.1:5123/api/cad/point

The endpoint on port 5123 is hosted by Toltech.App.
"""

import json
import threading

from http.server import (
    BaseHTTPRequestHandler,
    ThreadingHTTPServer
)

from ToltechPicker import get_picker


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Address used by the local FreeCAD bridge.
HOST = "127.0.0.1"

# Port used for communication:
#
# Toltech.App
#      |
#      | POST /api/cad/pick-point
#      v
# FreeCAD
#
PORT = 5124


class ToltechRequestHandler(BaseHTTPRequestHandler):
    """
    HTTP request handler used by the FreeCAD bridge.
    """

    def log_message(self, format, *args):
        """
        Redirect HTTP server messages to the FreeCAD console.
        """

        import FreeCAD

        FreeCAD.Console.PrintMessage(
            "Toltech HTTP: "
            + (format % args)
            + "\n"
        )

    def do_POST(self):
        """
        Handles POST requests coming from Toltech.App.
        """

        # Endpoint used to start point picking.
        if self.path == "/api/cad/pick-point":

            self._handle_pick_point()

            return

            # Demande de sélection d'une arête.
        if self.path == "/api/cad/pick-edge":
            self._handle_pick_edge()
            return

        if self.path == "/api/cad/stop-selection":
             self._handle_stop_selection()
             return

        # Unknown endpoint.
        self._send_json(
            status=404,
            data={
                "error": "Unknown endpoint"
            }
        )

    def _handle_pick_point(self):
        """
        Activates FreeCAD point selection.
        """

        try:

            # Activate the shared picker.
            get_picker().pick_point()

            # Inform Toltech that point picking
            # has been successfully activated.
            self._send_json(
                status=200,
                data={
                    "status": "picking"
                }
            )

        except Exception as error:

            # Return an HTTP 500 error if FreeCAD
            # cannot activate the picker.
            self._send_json(
                status=500,
                data={
                    "error": str(error)
                }
            )
  
    def _handle_stop_selection(self):
        """
        Arrête la sélection actuellement active dans FreeCAD.
        """

        try:
            # Désactive le callback souris du picker.
            get_picker().stop()

            self._send_json(
                status=200,
                data={
                    "status": "stopped"
                }
            )

        except Exception as error:
            self._send_json(
                status=500,
                data={
                    "error": str(error)
                }
            )
   
    def _send_json(self, status, data):
        """
        Sends a JSON HTTP response.
        """

        # Convert the response object into JSON.
        body = json.dumps(
            data
        ).encode("utf-8")

        # HTTP status.
        self.send_response(status)

        # Response content type.
        self.send_header(
            "Content-Type",
            "application/json"
        )

        # Response size.
        self.send_header(
            "Content-Length",
            str(len(body))
        )

        # End HTTP headers.
        self.end_headers()

        # Send response body.
        self.wfile.write(body)

    def _handle_pick_edge(self):
        """
        Activates FreeCAD edge selection.
        """

        try:
            # Demande au picker d'attendre
            # la sélection d'une arête.
            get_picker().pick_edge()

            self._send_json(
                status=200,
                data={
                    "status": "picking-edge"
                }
            )

        except Exception as error:

            self._send_json(
                status=500,
                data={
                    "error": str(error)
                }
            )


class ToltechServer:
    """
    Background HTTP server for the FreeCAD bridge.
    """

    def __init__(
        self,
        host=HOST,
        port=PORT
    ):
        """
        Creates the HTTP server.
        """

        self.host = host
        self.port = port

        # Create the HTTP server.
        self.server = ThreadingHTTPServer(
            (self.host, self.port),
            ToltechRequestHandler
        )

        # Server thread.
        self.thread = None

    def start(self):
        """
        Starts the HTTP server in a background thread.
        """

        # Do not start it twice.
        if self.thread is not None:
            return

        self.thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True
        )

        self.thread.start()

    def stop(self):
        """
        Stops the HTTP server.
        """

        if self.server is not None:

            self.server.shutdown()
            self.server.server_close()

        self.thread = None


# ---------------------------------------------------------------------------
# Global server instance
# ---------------------------------------------------------------------------

_server_instance = None


def start_server():
    """
    Starts the global Toltech HTTP server.

    Returns:
        ToltechServer: running server instance.
    """

    global _server_instance

    # Create and start the server only once.
    if _server_instance is None:

        _server_instance = ToltechServer()

        _server_instance.start()

        import FreeCAD

        FreeCAD.Console.PrintMessage(
            "Toltech: FreeCAD bridge started on "
            f"http://{HOST}:{PORT}\n"
        )

    return _server_instance


def stop_server():
    """
    Stops the global Toltech HTTP server.
    """

    global _server_instance

    if _server_instance is not None:

        _server_instance.stop()

        _server_instance = None

        import FreeCAD

        FreeCAD.Console.PrintMessage(
            "Toltech: FreeCAD bridge stopped.\n"
        )