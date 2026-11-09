using System.Text.Json;
using System.Text.Json.Serialization;

namespace Saathi.Client;

// C# records that mirror the API's JSON (api/app/models/schemas.py).
// JsonPropertyName maps C# PascalCase names to the API's snake_case field names.
public record ChatRequest(
    [property: JsonPropertyName("customer_id")] string CustomerId,
    [property: JsonPropertyName("question")] string Question,
    [property: JsonPropertyName("session_id")] string? SessionId = null);

// Which document, clause and version an answer is based on.
public record Citation(
    [property: JsonPropertyName("source_id")] string SourceId,
    [property: JsonPropertyName("clause_id")] string ClauseId,
    [property: JsonPropertyName("version")] string Version);

// What POST /chat returns. Comparison is only set for "Silver vs Gold" style questions.
public record ChatResponse(
    [property: JsonPropertyName("answer")] string Answer,
    [property: JsonPropertyName("intent")] string Intent,
    [property: JsonPropertyName("citations")] List<Citation> Citations,
    [property: JsonPropertyName("session_id")] string SessionId,
    [property: JsonPropertyName("comparison")] Comparison? Comparison = null,
    [property: JsonPropertyName("resolved_question")] string? ResolvedQuestion = null,
    [property: JsonPropertyName("intent_confidence")] double? IntentConfidence = null,
    [property: JsonPropertyName("intent_model")] string? IntentModel = null,
    [property: JsonPropertyName("intent_scores")] Dictionary<string, double>? IntentScores = null,
    [property: JsonPropertyName("intent_features")] List<TermWeight>? IntentFeatures = null,
    [property: JsonPropertyName("retriever")] string? Retriever = null,
    [property: JsonPropertyName("search_query")] string? SearchQuery = null,
    [property: JsonPropertyName("search_filter")] Dictionary<string, string>? SearchFilter = null,
    [property: JsonPropertyName("retrieved")] List<RetrievedClause>? Retrieved = null);

// A word or phrase from the question and how much it pushed the TF-IDF model towards the predicted intent.
public record TermWeight(
    [property: JsonPropertyName("term")] string Term,
    [property: JsonPropertyName("weight")] double Weight);

// One ranked search hit behind a /chat answer. Used = the answer cites it.
public record RetrievedClause(
    [property: JsonPropertyName("source_id")] string SourceId,
    [property: JsonPropertyName("clause_id")] string ClauseId,
    [property: JsonPropertyName("version")] string Version,
    [property: JsonPropertyName("text")] string Text,
    [property: JsonPropertyName("score")] double Score,
    [property: JsonPropertyName("used")] bool Used);

// POST /agent/chat: the Semantic Kernel agent's answer plus one entry per MCP tool call.
public record AgentToolCall(
    [property: JsonPropertyName("tool")] string Tool,
    [property: JsonPropertyName("args")] Dictionary<string, JsonElement> Args,
    [property: JsonPropertyName("ok")] bool Ok);

public record AgentChatResponse(
    [property: JsonPropertyName("answer")] string Answer,
    [property: JsonPropertyName("citations")] List<Citation> Citations,
    [property: JsonPropertyName("trace")] List<AgentToolCall> Trace,
    [property: JsonPropertyName("orchestrator")] string Orchestrator,
    // The draft the agent's save_draft tool created in this request, if any (still PENDING_APPROVAL).
    [property: JsonPropertyName("draft")] Draft? Draft = null);

// Comparison table: one row per aspect, one cell per tier (null cell = "Not stated").
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

// A customer's CRM record (only the fields the UI shows).
public record Customer(
    [property: JsonPropertyName("customer_id")] string CustomerId,
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("product")] string Product,
    [property: JsonPropertyName("tier")] string Tier,
    [property: JsonPropertyName("consent")] bool? Consent = null,
    [property: JsonPropertyName("renewal_date")] string? RenewalDate = null,
    [property: JsonPropertyName("policy_status")] string? PolicyStatus = null);

// GET /customers/{id}/sentiment: Azure AI Language label per interaction, plus the 90-day score.
public record SentimentReport(
    [property: JsonPropertyName("customer_id")] string CustomerId,
    [property: JsonPropertyName("sentiment_score_90d")] double? Score90d,
    [property: JsonPropertyName("as_of_date")] string? AsOfDate,
    [property: JsonPropertyName("interactions")] List<InteractionSentiment> Interactions);

public record InteractionSentiment(
    [property: JsonPropertyName("interaction_id")] string InteractionId,
    [property: JsonPropertyName("date")] string? Date,
    [property: JsonPropertyName("channel")] string? Channel,
    [property: JsonPropertyName("text")] string? Text,
    [property: JsonPropertyName("sentiment")] string? Sentiment,
    [property: JsonPropertyName("confidence_scores")] Dictionary<string, double>? Confidence);

// GET /worklist?details=true: the Renewal Radar, highest lapse risk first.
public record Worklist(
    [property: JsonPropertyName("items")] List<RadarItem> Items,
    [property: JsonPropertyName("synthetic")] bool Synthetic);

public record RadarItem(
    [property: JsonPropertyName("customer_id")] string CustomerId,
    [property: JsonPropertyName("risk_score")] double RiskScore,
    [property: JsonPropertyName("main_risk_factor")] string? MainRiskFactor,
    [property: JsonPropertyName("explanation_type")] string? ExplanationType = null,
    [property: JsonPropertyName("features")] List<RadarFeature>? Features = null,
    [property: JsonPropertyName("customer")] RadarCustomer? Customer = null);

public record RadarFeature(
    [property: JsonPropertyName("feature")] string Feature,
    [property: JsonPropertyName("label")] string Label,
    [property: JsonPropertyName("value")] double Value,
    [property: JsonPropertyName("contribution")] double? Contribution);

public record RadarCustomer(
    [property: JsonPropertyName("name")] string Name,
    [property: JsonPropertyName("product")] string Product,
    [property: JsonPropertyName("tier")] string Tier,
    [property: JsonPropertyName("renewal_date")] string? RenewalDate,
    [property: JsonPropertyName("policy_status")] string? PolicyStatus,
    [property: JsonPropertyName("consent")] bool? Consent);

// A renewal message draft. Status: PENDING_APPROVAL -> APPROVED -> SIMULATED_SENT.
public record Draft(
    [property: JsonPropertyName("draft_id")] string DraftId,
    [property: JsonPropertyName("customer_id")] string CustomerId,
    [property: JsonPropertyName("message")] string Message,
    [property: JsonPropertyName("status")] string Status,
    [property: JsonPropertyName("citations")] List<Citation> Citations);

// Result of GET /audit/verify.
public record AuditStatus(
    [property: JsonPropertyName("valid")] bool Valid,
    [property: JsonPropertyName("broken_at_seq")] int? BrokenAtSeq,
    [property: JsonPropertyName("total_events")] int TotalEvents);
