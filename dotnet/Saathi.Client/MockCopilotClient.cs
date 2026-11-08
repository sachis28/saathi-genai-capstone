using System.Text.Json;

namespace Saathi.Client;

// An in-memory fake of the API for offline demos and unit tests. It copies the real rules
// (approve before send, can't approve twice) so tests of the UI flow stay meaningful.
public class MockCopilotClient : ICopilotClient
{
    public event EventHandler<ChatResponse>? AnswerReceived;

    private readonly List<Customer> _customers = new()
    {
        new("C-204", "Demo Customer", "Health", "Silver"),
        new("C-311", "Mock Customer 2", "Motor", "Gold"),
    };

    private readonly Dictionary<string, Draft> _drafts = new();

    public Task<bool> HealthAsync() => Task.FromResult(true);

    public Task<ApiResult<Customer>> GetCustomerAsync(string customerId)
    {
        var c = _customers.FirstOrDefault(x => x.CustomerId == customerId);
        var result = c is null
            ? ApiResult<Customer>.Fail("404: Customer not found")
            : ApiResult<Customer>.Ok(c);
        return Task.FromResult(result);
    }

    public Task<ApiResult<ChatResponse>> ChatAsync(ChatRequest request)
    {
        var resp = new ChatResponse(
            "Mock answer",
            "policy_question",
            new List<Citation> { new("MOCK-DOC", "CL-0", "v0") },
            request.SessionId ?? Guid.NewGuid().ToString());

        AnswerReceived?.Invoke(this, resp);
        return Task.FromResult(ApiResult<ChatResponse>.Ok(resp));
    }

    // Builds a fake agent trace that looks like the real Semantic Kernel response.
    public Task<ApiResult<AgentChatResponse>> AgentChatAsync(ChatRequest request)
    {
        // Small helper: turn a string into a JsonElement (the type tool arguments use).
        JsonElement J(string v) => JsonSerializer.SerializeToElement(v);
        var trace = new List<AgentToolCall>
        {
            new("lookup_customer", new() { ["customer_id"] = J(request.CustomerId) }, true),
            new("search_knowledge_base", new() { ["query"] = J(request.Question), ["product"] = J(""), ["tier"] = J("") }, true),
        };
        var resp = new AgentChatResponse("Mock agent answer",
            new List<Citation> { new("MOCK-DOC", "CL-0", "v0") }, trace, "semantic-kernel");
        return Task.FromResult(ApiResult<AgentChatResponse>.Ok(resp));
    }

    public Task<ApiResult<Draft>> CreateDraftAsync(string customerId)
    {
        var c = _customers.FirstOrDefault(x => x.CustomerId == customerId);
        if (c is null)
            return Task.FromResult(ApiResult<Draft>.Fail("404: Customer not found"));

        var draft = new Draft(
            Guid.NewGuid().ToString(),
            c.CustomerId,
            $"Dear {c.Name}, your {c.Product} {c.Tier} policy is due for renewal.",
            "PENDING_APPROVAL",
            new List<Citation> { new("MOCK-DOC", "CL-REN-01", "v0") });

        _drafts[draft.DraftId] = draft;
        return Task.FromResult(ApiResult<Draft>.Ok(draft));
    }

    public Task<ApiResult<Draft>> ApproveDraftAsync(string draftId)
    {
        if (!_drafts.TryGetValue(draftId, out var d))
            return Task.FromResult(ApiResult<Draft>.Fail("404: Draft not found"));
        if (d.Status != "PENDING_APPROVAL")
            return Task.FromResult(ApiResult<Draft>.Fail($"409: Cannot approve a draft in status {d.Status}"));

        // Records are immutable; "with" makes a copy with only the Status changed.
        d = d with { Status = "APPROVED" };
        _drafts[draftId] = d;
        return Task.FromResult(ApiResult<Draft>.Ok(d));
    }

    public Task<ApiResult<Draft>> SendDraftAsync(string draftId)
    {
        if (!_drafts.TryGetValue(draftId, out var d))
            return Task.FromResult(ApiResult<Draft>.Fail("404: Draft not found"));
        if (d.Status != "APPROVED")
            return Task.FromResult(ApiResult<Draft>.Fail("409: BLOCKED: draft must be approved by the agent before sending"));

        d = d with { Status = "SIMULATED_SENT" };
        _drafts[draftId] = d;
        return Task.FromResult(ApiResult<Draft>.Ok(d));
    }

    public Task<ApiResult<AuditStatus>> VerifyAuditAsync() =>
        Task.FromResult(ApiResult<AuditStatus>.Ok(new AuditStatus(true, null, 0)));
}
