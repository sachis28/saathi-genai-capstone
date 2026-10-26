namespace Saathi.Client;

public class ChatSession
{
    public string SessionId { get; } = Guid.NewGuid().ToString();
}