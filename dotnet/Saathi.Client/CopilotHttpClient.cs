using System.Net.Http.Json;

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

    public async Task<ApiResult<Customer>> GetCustomerAsync(string customerId)
    {
        try
        {
            var r = await _http.GetAsync($"/customers/{customerId}");
            if (!r.IsSuccessStatusCode)
                throw new SaathiApiException($"Customer {customerId} not found", (int)r.StatusCode);

            var customer = await r.Content.ReadFromJsonAsync<Customer>();
            return ApiResult<Customer>.Ok(customer!);
        }
        catch (SaathiApiException ex)
        {
            return ApiResult<Customer>.Fail($"{ex.StatusCode}: {ex.Message}");
        }
        catch (HttpRequestException ex)
        {
            return ApiResult<Customer>.Fail("API unreachable: " + ex.Message);
        }
    }

    public async Task<ApiResult<ChatResponse>> ChatAsync(ChatRequest request)
    {
        try
        {
            var r = await _http.PostAsJsonAsync("/chat", request);
            if (!r.IsSuccessStatusCode)
                throw new SaathiApiException("Chat failed", (int)r.StatusCode);

            var resp = await r.Content.ReadFromJsonAsync<ChatResponse>();
            AnswerReceived?.Invoke(this, resp!);
            return ApiResult<ChatResponse>.Ok(resp!);
        }
        catch (SaathiApiException ex)
        {
            return ApiResult<ChatResponse>.Fail($"{ex.StatusCode}: {ex.Message}");
        }
        catch (HttpRequestException ex)
        {
            return ApiResult<ChatResponse>.Fail("API unreachable: " + ex.Message);
        }
    }
}