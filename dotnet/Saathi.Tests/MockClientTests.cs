using Saathi.Client;

namespace Saathi.Tests;

public class MockClientTests
{
    [Fact]
    public async Task Unknown_customer_returns_fail()
    {
        ICopilotClient c = new MockCopilotClient();
        var r = await c.GetCustomerAsync("C-999");
        Assert.False(r.Success);
    }

    [Fact]
    public async Task Chat_raises_event()
    {
        var c = new MockCopilotClient();
        var fired = false;
        c.AnswerReceived += (_, _) => fired = true;
        await c.ChatAsync(new ChatRequest("C-204", "hi"));
        Assert.True(fired);
    }
}
