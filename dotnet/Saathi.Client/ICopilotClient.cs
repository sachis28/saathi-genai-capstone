namespace Saathi.Client;

public interface ICopilotClient
{
    event EventHandler<ChatResponse>? AnswerReceived;

    Task<bool> HealthAsync();
    Task<ApiResult<Customer>> GetCustomerAsync(string customerId);
    Task<ApiResult<ChatResponse>> ChatAsync(ChatRequest request);

    Task<ApiResult<Draft>> CreateDraftAsync(string customerId);
    Task<ApiResult<Draft>> ApproveDraftAsync(string draftId);
    Task<ApiResult<Draft>> SendDraftAsync(string draftId);

    Task<ApiResult<AuditStatus>> VerifyAuditAsync();
}
