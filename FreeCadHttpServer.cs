using System.Net;
using System.Text;
using System.Text.Json;
using Toltech.Cad.Abstractions;
using Toltech.Cad.Model;
using static Toltech.Cad.Model.CadSelection;

namespace Toltech.FreeCAD;

/// <summary>
/// Serveur HTTP local utilisé pour recevoir les données
/// envoyées par le plugin FreeCAD vers Toltech.
/// </summary>
public sealed class FreeCadHttpServer
{
    private readonly HttpListener _listener;

    /// <summary>
    /// Service responsable de gérer les sélections FreeCAD.
    /// </summary>
    private readonly ICadSelectionService _selectionService;

    private CancellationTokenSource? _cancellationTokenSource;

    private Task? _serverTask;

    /// <summary>
    /// Constructeur.
    /// </summary>
    public FreeCadHttpServer(
        ICadSelectionService selectionService)
    {
        _selectionService = selectionService;

        _listener = new HttpListener();

        // Le serveur est accessible uniquement depuis
        // la machine locale.
        _listener.Prefixes.Add(
            "http://127.0.0.1:5123/");
    }

    /// <summary>
    /// Démarre le serveur HTTP.
    /// </summary>
    public void Start()
    {
        // Évite un double démarrage.
        if (_cancellationTokenSource is not null)
            return;

        _cancellationTokenSource =
            new CancellationTokenSource();

        // Lance la boucle HTTP en arrière-plan.
        _serverTask =
            ListenAsync(
                _cancellationTokenSource.Token);
    }

    /// <summary>
    /// Arrête le serveur HTTP.
    /// </summary>
    public void Stop()
    {
        _cancellationTokenSource?.Cancel();

        // Interrompt GetContextAsync().
        _listener.Stop();

        _cancellationTokenSource?.Dispose();

        _cancellationTokenSource = null;
        _serverTask = null;
    }

    /// <summary>
    /// Boucle principale d'écoute HTTP.
    /// </summary>
    private async Task ListenAsync(
        CancellationToken cancellationToken)
    {
        _listener.Start();

        while (!cancellationToken.IsCancellationRequested)
        {
            try
            {
                // Attend une nouvelle requête HTTP.
                HttpListenerContext context =
                    await _listener.GetContextAsync();

                // Traite la requête sans bloquer
                // l'écoute des suivantes.
                _ = HandleRequestAsync(context);
            }
            catch (HttpListenerException)
            {
                // Normal lorsque Stop() arrête le listener.
                break;
            }
            catch (ObjectDisposedException)
            {
                break;
            }
        }
    }

    /// <summary>
    /// Analyse une requête HTTP reçue.
    /// </summary>
    private async Task HandleRequestAsync(
        HttpListenerContext context)
    {
        try
        {
            string path =
                context.Request.Url?.AbsolutePath
                ?? string.Empty;

            string method =
                context.Request.HttpMethod;

            // -------------------------------------------------------------
            // Point
            // -------------------------------------------------------------

            if (method == "POST"
                && path == "/api/cad/point")
            {
                await HandlePointAsync(context);
                return;
            }

            // -------------------------------------------------------------
            // Edge
            // -------------------------------------------------------------

            if (method == "POST"
                && path == "/api/cad/edge")
            {
                await HandleEdgeAsync(context);
                return;
            }

            // -------------------------------------------------------------
            // Hint
            // -------------------------------------------------------------

            if (method == "POST"
                && path == "/api/cad/hint")
            {
                await HandleHintAsync(context);
                return;
            }

            // -------------------------------------------------------------
            // Endpoint inconnu
            // -------------------------------------------------------------

            await SendJsonAsync(
                context,
                HttpStatusCode.NotFound,
                new
                {
                    error = "Unknown endpoint"
                });
        }
        catch (Exception error)
        {
            try
            {
                await SendJsonAsync(
                    context,
                    HttpStatusCode.InternalServerError,
                    new
                    {
                        error = error.Message
                    });
            }
            catch
            {
                // La connexion HTTP peut déjà être fermée.
            }
        }
    }

    // =====================================================================
    // POINT
    // =====================================================================

    /// <summary>
    /// Reçoit un point envoyé par FreeCAD.
    /// </summary>
    private async Task HandlePointAsync(
        HttpListenerContext context)
    {
        string json =
            await ReadRequestBodyAsync(context);

        CadPoint? point;

        try
        {
            point =
                JsonSerializer.Deserialize<CadPoint>(
                    json);
        }
        catch (JsonException)
        {
            await SendJsonAsync(
                context,
                HttpStatusCode.BadRequest,
                new
                {
                    error = "Invalid point JSON"
                });

            return;
        }

        if (point is null)
        {
            await SendJsonAsync(
                context,
                HttpStatusCode.BadRequest,
                new
                {
                    error = "Point is null"
                });

            return;
        }

        // Transmission de la sélection au service CAO.
        _selectionService.ReceiveSelection(
            new CadSelection(point));

        await SendJsonAsync(
            context,
            HttpStatusCode.OK,
            new
            {
                status = "received"
            });
    }

    // =====================================================================
    // EDGE
    // =====================================================================

    /// <summary>
    /// Reçoit une direction d'arête envoyée par FreeCAD.
    /// </summary>
    private async Task HandleEdgeAsync(
        HttpListenerContext context)
    {
        string json =
            await ReadRequestBodyAsync(context);

        CadDirection? direction;

        try
        {
            direction =
                JsonSerializer.Deserialize<CadDirection>(
                    json);
        }
        catch (JsonException)
        {
            await SendJsonAsync(
                context,
                HttpStatusCode.BadRequest,
                new
                {
                    error = "Invalid direction JSON"
                });

            return;
        }

        if (direction is null)
        {
            await SendJsonAsync(
                context,
                HttpStatusCode.BadRequest,
                new
                {
                    error = "Direction is null"
                });

            return;
        }

        // Transformation en sélection générique.
        _selectionService.ReceiveSelection(
            new CadSelection(direction));

        await SendJsonAsync(
            context,
            HttpStatusCode.OK,
            new
            {
                status = "received"
            });
    }

    // =====================================================================
    // HINT
    // =====================================================================

    /// <summary>
    /// Reçoit un message utilisateur envoyé par FreeCAD.
    ///
    /// Ce endpoint ne correspond pas à une sélection CAO.
    /// Il sert uniquement à informer l'interface Toltech.
    /// </summary>
    /// <summary>
    /// Reçoit un message d'information envoyé par FreeCAD.
    /// </summary>
    private async Task HandleHintAsync(
     HttpListenerContext context)
    {
        using StreamReader reader =
            new(
                context.Request.InputStream,
                context.Request.ContentEncoding);

        string json =
            await reader.ReadToEndAsync();

        CadHint? hint;

        try
        {
            hint = JsonSerializer.Deserialize<CadHint>(
                json,
                new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                });
        }
        catch (JsonException error)
        {
            await SendJsonAsync(
                context,
                HttpStatusCode.BadRequest,
                new
                {
                    error = "Invalid hint JSON",
                    details = error.Message
                });

            return;
        }

        if (hint is null ||
            string.IsNullOrWhiteSpace(hint.Message))
        {
            await SendJsonAsync(
                context,
                HttpStatusCode.BadRequest,
                new
                {
                    error = "Hint message is empty"
                });

            return;
        }

        // Transmission du message au service CAO.
        _selectionService.ReceiveHint(
            hint.Message);

        await SendJsonAsync(
            context,
            HttpStatusCode.OK,
            new
            {
                status = "received"
            });
    }

    // =====================================================================
    // HTTP helpers
    // =====================================================================

    /// <summary>
    /// Lit le corps JSON d'une requête HTTP.
    /// </summary>
    private static async Task<string> ReadRequestBodyAsync(
        HttpListenerContext context)
    {
        using StreamReader reader =
            new(
                context.Request.InputStream,
                context.Request.ContentEncoding);

        return await reader.ReadToEndAsync();
    }

    /// <summary>
    /// Envoie une réponse JSON au client HTTP.
    /// </summary>
    private static async Task SendJsonAsync(
        HttpListenerContext context,
        HttpStatusCode statusCode,
        object data)
    {
        string json =
            JsonSerializer.Serialize(data);

        byte[] bytes =
            Encoding.UTF8.GetBytes(json);

        context.Response.StatusCode =
            (int)statusCode;

        context.Response.ContentType =
            "application/json; charset=utf-8";

        context.Response.ContentLength64 =
            bytes.Length;

        try
        {
            await context.Response.OutputStream
                .WriteAsync(bytes);
        }
        finally
        {
            context.Response.Close();
        }
    }
}