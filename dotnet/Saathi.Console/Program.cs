using Saathi.Client;

var baseUrl = Environment.GetEnvironmentVariable("SAATHI_API_URL") ?? "http://localhost:8000";
ICopilotClient client = new CopilotHttpClient(new HttpClient { BaseAddress = new Uri(baseUrl) });

client.AnswerReceived += (sender, r) =>
    Console.WriteLine($"[event] answer received with {r.Citations.Count} citation(s)");

Console.WriteLine($"Health: {await client.HealthAsync()}");

foreach (var id in new[] { "C-204", "C-999" })
{
    var result = await client.GetCustomerAsync(id);
    Console.WriteLine(result.Success
        ? $"{id}: {result.Data!.Name} | {result.Data.Product} | {result.Data.Tier}"
        : $"{id}: ERROR {result.Error}");
}

var chat = await client.ChatAsync(new ChatRequest("C-204", "What is covered in Silver?"));
if (chat.Success)
{
    Console.WriteLine($"Answer: {chat.Data!.Answer}");
    var sources = chat.Data.Citations.Select(c => $"{c.SourceId}#{c.ClauseId}").ToList();
    Console.WriteLine("Citations: " + string.Join(", ", sources));
}
else
{
    Console.WriteLine("Chat ERROR: " + chat.Error);
}