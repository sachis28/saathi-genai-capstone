using Microsoft.Extensions.DependencyInjection;
using Saathi.Client;

var mode = Environment.GetEnvironmentVariable("SAATHI_MODE") ?? "Http";
var baseUrl = Environment.GetEnvironmentVariable("SAATHI_API_URL") ?? "http://localhost:8000";

var services = new ServiceCollection();
services.AddSaathiClient(mode, baseUrl);
using var provider = services.BuildServiceProvider();

Console.WriteLine($"Mode: {mode}");
Console.WriteLine("---- Lifetime demo ----");

var f1 = provider.GetRequiredService<ICopilotClientFactory>();
var f2 = provider.GetRequiredService<ICopilotClientFactory>();
Console.WriteLine($"Singleton factory  -> same instance: {ReferenceEquals(f1, f2)}");

var c1 = provider.GetRequiredService<ICopilotClient>();
var c2 = provider.GetRequiredService<ICopilotClient>();
Console.WriteLine($"Transient client   -> same instance: {ReferenceEquals(c1, c2)}");

string idA;
using (var scopeA = provider.CreateScope())
{
    var s1 = scopeA.ServiceProvider.GetRequiredService<ChatSession>();
    var s2 = scopeA.ServiceProvider.GetRequiredService<ChatSession>();
    Console.WriteLine($"Scoped session     -> same inside one scope: {ReferenceEquals(s1, s2)}");
    idA = s1.SessionId;
}

using (var scopeB = provider.CreateScope())
{
    var s3 = scopeB.ServiceProvider.GetRequiredService<ChatSession>();
    Console.WriteLine($"Scoped session     -> different across scopes: {idA != s3.SessionId}");
}

Console.WriteLine("---- Saathi call ----");

using var scope = provider.CreateScope();
var client = scope.ServiceProvider.GetRequiredService<ICopilotClient>();
var session = scope.ServiceProvider.GetRequiredService<ChatSession>();

Console.WriteLine($"Client type: {client.GetType().Name}");
Console.WriteLine($"Health: {await client.HealthAsync()}");

var customer = await client.GetCustomerAsync("C-204");
Console.WriteLine(customer.Success
    ? $"C-204: {customer.Data!.Name} | {customer.Data.Tier}"
    : $"C-204: ERROR {customer.Error}");

var chat = await client.ChatAsync(new ChatRequest("C-204", "What is covered in Silver?", session.SessionId));
Console.WriteLine(chat.Success
    ? $"Answer: {chat.Data!.Answer} | session: {chat.Data.SessionId}"
    : $"Chat ERROR: {chat.Error}");