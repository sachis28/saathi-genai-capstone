namespace Saathi.Client;

// Mock = fake data inside the app (no API needed); Http = call the real Python API.
public enum ClientMode
{
    Mock,
    Http
}

// The Factory pattern: code asks the factory for a client and doesn't care which kind it gets.
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

    // Pick the implementation from the configured mode.
    public ICopilotClient Create()
    {
        return _mode switch
        {
            ClientMode.Mock => new MockCopilotClient(),
            // "saathi" is the named HttpClient set up in ServiceCollectionExtensions (with the API base URL).
            _ => new CopilotHttpClient(_httpFactory.CreateClient("saathi"))
        };
    }
}