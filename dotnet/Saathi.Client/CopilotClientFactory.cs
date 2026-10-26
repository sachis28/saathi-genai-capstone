namespace Saathi.Client;

public enum ClientMode
{
    Mock,
    Http
}

public interface ICopilotClientFactory
{
    ICopilotClient Create();
}

public class CopilotClientFactory : ICopilotClientFactory
{
    private readonly IHttpClientFactory _httpFactory;
    private readonly ClientMode _mode;

    public CopilotClientFactory(IHttpClientFactory httpFactory, ClientMode mode)
    {
        _httpFactory = httpFactory;
        _mode = mode;
    }

    public ICopilotClient Create()
    {
        return _mode switch
        {
            ClientMode.Mock => new MockCopilotClient(),
            _ => new CopilotHttpClient(_httpFactory.CreateClient("saathi"))
        };
    }
}