using System.Text.Json.Serialization;

namespace Saathi.Client;

public record ChatRequest(
    [property: JsonPropertyName("customer_id")] string CustomerId,
    [property: JsonPropertyName("question")] string Question,
    [property: JsonPropertyName("session_id")] string? SessionId = null);

public record Citation(
    [property: JsonPropertyName("source_id")] string SourceId,
    [property: JsonPropertyName("clause_id")] string ClauseId,
    [property: JsonPropertyName("version")] string Version);

public record ChatResponse(
    [property: JsonPropertyName("answer")] string Answer,
    [property: JsonPropertyName("intent")] string Intent,
    [property: JsonPropertyName("citations")] List<Citation> Citations,
    [property: JsonPropertyName("session_id")] string SessionId);

public record Customer(
    [property: JsonPropertyName("customer_id")] string CustomerId,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("product")] string Product,
    [property: JsonPropertyName("tier")] string Tier);