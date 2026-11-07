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
    [property: JsonPropertyName("session_id")] string SessionId,
    [property: JsonPropertyName("comparison")] Comparison? Comparison = null);

public record ComparisonCell(
    [property: JsonPropertyName("text")] string Text,
    [property: JsonPropertyName("source_id")] string SourceId,
    [property: JsonPropertyName("clause_id")] string ClauseId,
    [property: JsonPropertyName("version")] string Version);

public record ComparisonRow(
    [property: JsonPropertyName("aspect")] string Aspect,
    [property: JsonPropertyName("cells")] Dictionary<string, ComparisonCell?> Cells);

public record Comparison(
    [property: JsonPropertyName("product")] string Product,
    [property: JsonPropertyName("tiers")] List<string> Tiers,
    [property: JsonPropertyName("rows")] List<ComparisonRow> Rows);

public record Customer(
    [property: JsonPropertyName("customer_id")] string CustomerId,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("product")] string Product,
    [property: JsonPropertyName("tier")] string Tier);

public record Draft(
    [property: JsonPropertyName("draft_id")] string DraftId,
    [property: JsonPropertyName("customer_id")] string CustomerId,
    [property: JsonPropertyName("message")] string Message,
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("citations")] List<Citation> Citations);

public record AuditStatus(
    [property: JsonPropertyName("valid")] bool Valid,
    [property: JsonPropertyName("broken_at_seq")] int? BrokenAtSeq,
    [property: JsonPropertyName("total_events")] int TotalEvents);
