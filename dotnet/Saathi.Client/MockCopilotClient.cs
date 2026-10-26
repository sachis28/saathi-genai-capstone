namespace Saathi.Client;

public class MockCopilotClient : ICopilotClient
{
    public event EventHandler<ChatResponse>? AnswerReceived;

    private readonly List<Customer> _customers = new()
    {
        new("C-204", "Demo Customer", "Health", "Silver"),
        new("C-311", "Mock Customer 2", "Motor", "Gold"),
    };

    public Task<bool> HealthAsync() => Task.FromResult(true);

    public Task<ApiResult<Customer>> GetCustomerAsync(string customerId)
    {
        var c = _customers.FirstOrDefault(x => x.CustomerId == customerId);
        var result = c is null
            ? ApiResult<Customer>.Fail($"404: Customer {customerId} not found")
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
}