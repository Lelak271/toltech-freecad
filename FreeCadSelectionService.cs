using System.Net.Http;
using Toltech.Cad.Abstractions;
using Toltech.Cad.Model;
using static Toltech.Cad.Model.CadSelection;

namespace Toltech.FreeCAD;

/// <summary>
/// Implémentation du service de sélection pour FreeCAD.
/// </summary>
public sealed class FreeCadSelectionService : ICadSelectionService
{
    private readonly HttpClient _httpClient;

    /// <summary>
    /// Indique si FreeCAD est actuellement en mode sélection.
    /// </summary>
    private bool _selectionActive;

    /// <summary>
    /// Événement déclenché lorsqu'une entité est sélectionnée.
    /// </summary>
    public event EventHandler<CadSelection>? SelectionChanged;

    /// <summary>
    /// Événement déclenché lorsque le mode sélection est arrêté.
    /// </summary>
    public event EventHandler? SelectionStopped;

    public CadSoftware? ActiveSoftware { get; } = CadSoftware.FreeCAD;


    public event EventHandler<string>? HintReceived;

    public FreeCadSelectionService()
    {
        _httpClient = new HttpClient
        {
            BaseAddress = new Uri("http://127.0.0.1:5124")
        };
    }

    /// <summary>
    /// Démarre une sélection dans FreeCAD.
    /// </summary>
    public async Task StartSelectionAsync(
        CadSelectionType selectionType,
        CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();

        switch (selectionType)
        {
            case CadSelectionType.Point:

                await StartPointSelectionAsync(
                    cancellationToken);

                break;
            case CadSelectionType.Edge:

                await StartEdgeSelectionAsync(
                    cancellationToken);

                break;

            default:

                throw new NotSupportedException(
                    $"Le type de sélection " +
                    $"'{selectionType}' n'est pas encore " +
                    $"supporté par FreeCAD.");
        }

        _selectionActive = true;
    }

    /// <summary>
    /// Demande à FreeCAD d'activer la sélection
    /// d'un point.
    /// </summary>
    private async Task StartPointSelectionAsync(
        CancellationToken cancellationToken)
    {
        using HttpResponseMessage response =
            await _httpClient.PostAsync(
                "/api/cad/pick-point",
                content: null,
                cancellationToken);

        response.EnsureSuccessStatusCode();
    }

    /// <summary>
    /// Demande à FreeCAD d'activer la sélection
    /// d'un point.
    /// </summary>
    private async Task StartEdgeSelectionAsync(
        CancellationToken cancellationToken)
    {
        using HttpResponseMessage response =
            await _httpClient.PostAsync(
                "/api/cad/pick-edge",
                content: null,
                cancellationToken);

        response.EnsureSuccessStatusCode();
    }

    /// <summary>
    /// Arrête la sélection actuellement active.
    /// </summary>
    public async Task StopSelectionAsync(
        CancellationToken cancellationToken = default)
    {
        if (!_selectionActive)
            return;

        try
        {
            using HttpResponseMessage response =
                await _httpClient.PostAsync(
                    "/api/cad/stop-selection",
                    content: null,
                    cancellationToken);

            response.EnsureSuccessStatusCode();
        }
        catch (HttpRequestException)
        {
            // FreeCAD peut avoir été fermé entre-temps.
        }
        finally
        {
            _selectionActive = false;

            // Informe les abonnés que la sélection est terminée.
            SelectionStopped?.Invoke(
                this,
                EventArgs.Empty);
        }
    }

    /// <summary>
    /// Reçoit un message d'information provenant de FreeCAD.
    /// </summary>
    public void ReceiveHint(string message)
    {
        if (string.IsNullOrWhiteSpace(message))
            return;

        HintReceived?.Invoke(
            this,
            message);
    }

    /// <summary>
    /// Vérifie si le serveur FreeCAD répond.
    /// </summary>
    public async Task<bool> CheckConnectionAsync(
        CancellationToken cancellationToken = default)
    {
        try
        {
            using HttpResponseMessage response =
                await _httpClient.GetAsync(
                    "/api/cad/status",
                    cancellationToken);

            return response.IsSuccessStatusCode;
        }
        catch (HttpRequestException)
        {
            return false;
        }
        catch (TaskCanceledException)
        {
            return false;
        }
    }

    /// <summary>
    /// 
    /// </summary>
    public void ReceiveSelection(
    CadSelection selection)
    {
        _selectionActive = false;

        SelectionChanged?.Invoke(
            this,
            selection);
    }

}