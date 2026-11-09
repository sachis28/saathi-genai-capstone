namespace Saathi.Client;

// The contract both clients (Mock and Http) follow. The UI only knows this interface,
// so we can swap the real API for the mock without changing any page code.
public interface ICopilotClient
{
    event EventHandler<ChatResponse>? AnswerReceived;

    Task<bool> HealthAsync();
    Task<ApiResult<Customer>> GetCustomerAsync(string customerId);
    Task<ApiResult<ChatResponse>> ChatAsync(ChatRequest request);
    Task<ApiResult<AgentChatResponse>> AgentChatAsync(ChatRequest request);

    Task<ApiResult<Draft>> CreateDraftAsync(string customerId);
    Task<ApiResult<Draft>> ApproveDraftAsync(string draftId);
    Task<ApiResult<Draft>> SendDraftAsync(string draftId);

    Task<ApiResult<AuditStatus>> VerifyAuditAsync();

    // Sentiment of the customer's past interactions (no login needed, like GET /customers/{id}).
    Task<ApiResult<SentimentReport>> GetSentimentAsync(string customerId);

    // Renewal Radar. agentToken is the agent's bearer token; the API decides which customers it sees.
    Task<ApiResult<Worklist>> GetWorklistAsync(string agentToken, int limit = 10);
}
