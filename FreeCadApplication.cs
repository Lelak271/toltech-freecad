using Toltech.Cad.Abstractions;

namespace Toltech.FreeCAD;

/// <summary>
/// Corps JSON reçu par l'endpoint /api/cad/hint.
/// </summary>
public sealed record CadHintRequest(
    string Message);

/// <summary>
/// Représente une instance CAD de FreeCAD
/// </summary>
public sealed class FreeCadApplication : ICadApplication
{
    private readonly FreeCadSelectionService _selectionService;

    /// <summary>
    /// Identifiant interne de FreeCAD.
    /// </summary>
    public string Id =>
        "FreeCAD";

    /// <summary>
    /// Nom affiché dans l'interface utilisateur.
    /// </summary>
    public CadSoftware Software => CadSoftware.FreeCAD;

    /// <summary>
    /// Indique si FreeCAD est actuellement accessible.
    /// </summary>
    public bool IsConnected
    {
        get;
        private set;
    }

    /// <summary>
    /// Service de sélection FreeCAD exposé
    /// sous son abstraction générique.
    /// </summary>
    public ICadSelectionService Selection =>
        _selectionService;

    /// <summary>
    /// Constructeur.
    /// </summary>
    public FreeCadApplication()
    {
        _selectionService = new FreeCadSelectionService();
    }

    /// <summary>
    /// Vérifie si le serveur FreeCAD répond.
    /// </summary>
    public async Task CheckConnectionAsync()
    {
        IsConnected =
            await ((FreeCadSelectionService)Selection)
                .CheckConnectionAsync();
    }
}