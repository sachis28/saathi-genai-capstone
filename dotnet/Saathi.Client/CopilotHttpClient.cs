using System.Net.Http.Json;
using System.Text.Json;

namespace Saathi.Client;

public class CopilotHttpClient : ICopilotClient
{
    private readonly HttpClient _http;

    public event EventHandler<ChatResponse>? AnswerReceived;

    public CopilotHttpClient(HttpClient http)
    {
        _http = http;
    }

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

    public Task<ApiResult<Customer>> GetCustomerAsync(string customerId) =>
        CallAsync<Customer>(() => _http.GetAsync($"/customers/{Uri.EscapeDataString(customerId)}"));

    public async Task<ApiResult<ChatResponse>> ChatAsync(ChatRequest request)
    {
        var result = await CallAsync<ChatResponse>(() => _http.PostAsJsonAsync("/chat", request));
        if (result.Success)
            AnswerReceived?.Invoke(this, result.Data!);
        return result;
    }

    public Task<ApiResult<AgentChatResponse>> AgentChatAsync(ChatRequest request) =>
        CallAsync<AgentChatResponse>(() => _http.PostAsJsonAsync("/agent/chat", request));

    public Task<ApiResult<Draft>> CreateDraftAsync(string customerId) =>
        CallAsync<Draft>(() => _http.PostAsJsonAsync("/drafts", new { customer_id = customerId }));

    public Task<ApiResult<Draft>> ApproveDraftAsync(string draftId) =>
        CallAsync<Draft>(() => _http.PostAsync($"/drafts/{Uri.EscapeDataString(draftId)}/approve", null));

    public Task<ApiResult<Draft>> SendDraftAsync(string draftId) =>
        CallAsync<Draft>(() => _http.PostAsync($"/drafts/{Uri.EscapeDataString(draftId)}/send", null));

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
