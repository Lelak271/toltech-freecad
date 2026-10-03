"""
Toltech FreeCAD GUI integration.

This file is loaded automatically by FreeCAD.
It starts the HTTP bridge and registers the Toltech Workbench.
"""

import FreeCAD
import FreeCADGui

from ToltechServer import start_server


# ============================================================================
# 1. Start the HTTP server
# ============================================================================

try:
    # The server listens on:
    #
    #     http://127.0.0.1:5124
    #
    # It receives commands from Toltech.App.
    _server = start_server()

    FreeCAD.Console.PrintMessage(
        "Toltech: HTTP bridge started successfully.\n"
    )

except Exception as error:

    _server = None

    FreeCAD.Console.PrintError(
        "Toltech: unable to start HTTP bridge: "
        + str(error)
        + "\n"
    )


# ============================================================================
# 2. Toltech point-picking command
# ============================================================================

class ToltechPickPointCommand:
    """
    FreeCAD command used to activate point selection.
    """

    def GetResources(self):
        """
        Defines the command displayed by FreeCAD.
        """

        return {
            "MenuText": "Pick point for Toltech",
            "ToolTip": "Select a 3D point for Toltech"
        }

    def Activated(self):
        """
        Called when the user activates the command.
        """

        from ToltechPicker import get_picker

        # Activate the FreeCAD point picker.
        get_picker().pick_point()

    def IsActive(self):
        """
        The command is available when a document is open.
        """

        return FreeCAD.ActiveDocument is not None


# ============================================================================
# 3. Register the FreeCAD command
# ============================================================================

try:

    FreeCADGui.addCommand(
        "Toltech_PickPoint",
        ToltechPickPointCommand()
    )

    FreeCAD.Console.PrintMessage(
        "Toltech: PickPoint command registered.\n"
    )

except Exception as error:

    FreeCAD.Console.PrintError(
        "Toltech: unable to register PickPoint command: "
        + str(error)
        + "\n"
    )


# ============================================================================
# 4. Toltech Workbench
# ============================================================================

class ToltechWorkbench(FreeCADGui.Workbench):
    """
    Toltech FreeCAD Workbench.
    """
    MenuText = "Toltech"
    ToolTip = "Toltech integration"

    def Initialize(self):
        """
        Called by FreeCAD when the Toltech Workbench is activated.
        """
        FreeCAD.Console.PrintMessage(
            "Toltech: Workbench initialized.\n"
        )
        # Add the point-picking command to the Toltech menu.
        self.appendMenu(
            "Toltech",
            [
                "Toltech_PickPoint"
            ]
        )

    def GetClassName(self):
        """
        Returns the FreeCAD Python Workbench type.
        """
        return "Gui::PythonWorkbench"

# ============================================================================
# 5. Register the Workbench
# ============================================================================
FreeCADGui.addWorkbench(ToltechWorkbench())