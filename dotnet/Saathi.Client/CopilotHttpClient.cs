using System.Net.Http.Json;
using System.Text.Json;

namespace Saathi.Client;

// The real client: every method is one HTTP call to the FastAPI backend.
public class CopilotHttpClient : ICopilotClient
{
    private readonly HttpClient _http;

    // Raised after every successful /chat answer, so other parts of the UI can react to it.
    public event EventHandler<ChatResponse>? AnswerReceived;

    public CopilotHttpClient(HttpClient http)
    {
        _http = http;
    }

    // GET /health. Returns false instead of throwing when the API is down.
    public async Task<bool> HealthAsync()
    {
        try
        {
            var r = await _http.GetAsync("/health");
            return r.IsSuccessStatusCode;
        }
        catch (HttpRequestException)
        {
            return false;
        }
    }

    // Uri.EscapeDataString keeps user-typed ids from breaking or changing the URL.
    public Task<ApiResult<Customer>> GetCustomerAsync(string customerId) =>
        CallAsync<Customer>(() => _http.GetAsync($"/customers/{Uri.EscapeDataString(customerId)}"));

    // POST /chat: the grounded RAG answer with citations.
    public async Task<ApiResult<ChatResponse>> ChatAsync(ChatRequest request)
    {
        var result = await CallAsync<ChatResponse>(() => _http.PostAsJsonAsync("/chat", request));
        if (result.Success)
            AnswerReceived?.Invoke(this, result.Data!);
        return result;
    }

    // POST /agent/chat: the Semantic Kernel agent's answer plus its tool-call trace.
    public Task<ApiResult<AgentChatResponse>> AgentChatAsync(ChatRequest request) =>
        CallAsync<AgentChatResponse>(() => _http.PostAsJsonAsync("/agent/chat", request));

    // The draft workflow: create -> approve (human) -> send (simulated).
    public Task<ApiResult<Draft>> CreateDraftAsync(string customerId) =>
        CallAsync<Draft>(() => _http.PostAsJsonAsync("/drafts", new { customer_id = customerId }));

    public Task<ApiResult<Draft>> ApproveDraftAsync(string draftId) =>
        CallAsync<Draft>(() => _http.PostAsync($"/drafts/{Uri.EscapeDataString(draftId)}/approve", null));

    public Task<ApiResult<Draft>> SendDraftAsync(string draftId) =>
        CallAsync<Draft>(() => _http.PostAsync($"/drafts/{Uri.EscapeDataString(draftId)}/send", null));

    // GET /audit/verify: is the audit hash chain intact?
    public Task<ApiResult<AuditStatus>> VerifyAuditAsync() =>
        CallAsync<AuditStatus>(() => _http.GetAsync("/audit/verify"));

    // One place for calling the API, reading errors and wrapping the result.
    private static async Task<ApiResult<T>> CallAsync<T>(Func<Task<HttpResponseMessage>> call)
    {
        try
        {
            var r = await call();
            if (!r.IsSuccessStatusCode)
                throw new SaathiApiException(await ReadDetailAsync(r), (int)r.StatusCode);

            var data = await r.Content.ReadFromJsonAsync<T>();
            return ApiResult<T>.Ok(data!);
        }
        catch (SaathiApiException ex)
        {
            return ApiResult<T>.Fail($"{ex.StatusCode}: {ex.Message}");
        }
        catch (HttpRequestException ex)
        {
            return ApiResult<T>.Fail("API unreachable: " + ex.Message);
        }
    }

    // FastAPI errors look like {"detail": "BLOCKED: ..."}
    private static async Task<string> ReadDetailAsync(HttpResponseMessage r)
    {
        try
        {
            var body = await r.Content.ReadAsStringAsync();
            using var doc = JsonDocument.Parse(body);
            if (doc.RootElement.TryGetProperty("detail", out var d) && d.ValueKind == JsonValueKind.String)
                return d.GetString()!;
        }
        catch (JsonException)
        {
        }
        return $"HTTP {(int)r.StatusCode}";
    }
}
