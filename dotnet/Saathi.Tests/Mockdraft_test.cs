using Saathi.Client;

namespace Saathi.Tests;

public class MockDraftTests
{
    [Fact]
    public async Task Send_before_approval_is_blocked()
    {
        ICopilotClient c = new MockCopilotClient();
        var draft = (await c.CreateDraftAsync("C-204")).Data!;

        var r = await c.SendDraftAsync(draft.DraftId);

        Assert.False(r.Success);
        Assert.Contains("BLOCKED", r.Error);
    }

    [Fact]
    public async Task Approve_then_send_works()
    {
        ICopilotClient c = new MockCopilotClient();
        var draft = (await c.CreateDraftAsync("C-204")).Data!;

        var approved = await c.ApproveDraftAsync(draft.DraftId);
        var sent = await c.SendDraftAsync(draft.DraftId);

        Assert.Equal("APPROVED", approved.Data!.Status);
        Assert.Equal("SIMULATED_SENT", sent.Data!.Status);
    }

    [Fact]
    public async Task Cannot_approve_twice()
    {
        ICopilotClient c = new MockCopilotClient();
        var draft = (await c.CreateDraftAsync("C-204")).Data!;

        await c.ApproveDraftAsync(draft.DraftId);
        var again = await c.ApproveDraftAsync(draft.DraftId);

        Assert.False(again.Success);
    }
}

