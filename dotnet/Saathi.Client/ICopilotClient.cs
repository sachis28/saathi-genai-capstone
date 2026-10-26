namespace Saathi.Client;

public interface ICopilotClient
{
    event EventHandler<ChatResponse>? AnswerReceived;

    Task<bool> HealthAsync();
    Task<ApiResult<Customer>> GetCustomerAsync(string customerId);
    Task<ApiResult<ChatResponse>> ChatAsync(ChatRequest request);
}