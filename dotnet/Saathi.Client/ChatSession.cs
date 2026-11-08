namespace Saathi.Client;

// One chat conversation. Its SessionId is sent with every question so the API can remember
// earlier turns (e.g. "and Platinum?"). Registered as Scoped, so each user gets their own.
public class ChatSession
{
    public string SessionId { get; } = Guid.NewGuid().ToString();
}