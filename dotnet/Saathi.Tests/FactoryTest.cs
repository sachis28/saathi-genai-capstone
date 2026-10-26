using Microsoft.Extensions.DependencyInjection;
using Saathi.Client;

namespace Saathi.Tests;

public class FactoryTests
{
    private static ServiceProvider Build(string mode) =>
        new ServiceCollection()
            .AddSaathiClient(mode, "http://localhost:8000")
            .BuildServiceProvider();

    [Fact]
    public void Mock_mode_returns_mock_client()
    {
        using var sp = Build("Mock");
        Assert.IsType<MockCopilotClient>(sp.GetRequiredService<ICopilotClient>());
    }

    [Fact]
    public void Http_mode_returns_http_client()
    {
        using var sp = Build("Http");
        Assert.IsType<CopilotHttpClient>(sp.GetRequiredService<ICopilotClient>());
    }

    [Fact]
    public void Factory_is_singleton()
    {
        using var sp = Build("Mock");
        Assert.Same(sp.GetRequiredService<ICopilotClientFactory>(), sp.GetRequiredService<ICopilotClientFactory>());
    }

    [Fact]
    public void Session_is_different_per_scope()
    {
        using var sp = Build("Mock");
        using var a = sp.CreateScope();
        using var b = sp.CreateScope();
        Assert.NotEqual(
            a.ServiceProvider.GetRequiredService<ChatSession>().SessionId,
            b.ServiceProvider.GetRequiredService<ChatSession>().SessionId);
    }
}