using System.Text.Json;
using Saathi.Client;

namespace Saathi.Tests;

// Checks the agent response model: the mock trace is scoped to the customer, and the
// real API's JSON (tool trace, citations, resolved question) deserialises correctly.
public class AgentTraceTests
{
    [Fact]
    public async Task Mock_agent_returns_a_scoped_tool_trace()
    {
        ICopilotClient c = new MockCopilotClient();
        var r = await c.AgentChatAsync(new ChatRequest("C-204", "Is air ambulance covered?"));
        Assert.True(r.Success);
        Assert.Equal("semantic-kernel", r.Data!.Orchestrator);
        Assert.InRange(r.Data.Trace.Count, 1, 3);
        Assert.Equal("C-204", r.Data.Trace[0].Args["customer_id"].GetString());
    }

    [Fact]
    public void Agent_response_reads_the_api_json()
    {
        const string json = """
        {"answer":"Yes.","citations":[{"source_id":"SCAN-HEALTH-GOLD-END-17","clause_id":"CL-AIR-01","version":"v1"}],
         "trace":[{"tool":"search_knowledge_base","args":{"query":"air ambulance","product":"Health","tier":"Gold"},"ok":true,"orchestrator":"semantic-kernel"}],
         "orchestrator":"semantic-kernel"}
        """;
        var r = JsonSerializer.Deserialize<AgentChatResponse>(json)!;
        Assert.Equal("search_knowledge_base", r.Trace[0].Tool);
        Assert.Equal("Gold", r.Trace[0].Args["tier"].GetString());
        Assert.Equal("SCAN-HEALTH-GOLD-END-17", r.Citations[0].SourceId);
    }

    [Fact]
    public void Chat_response_reads_resolved_question()
    {
        const string json = """{"answer":"a","intent":"compare_products","citations":[],"session_id":"s","resolved_question":"full question"}""";
        Assert.Equal("full question", JsonSerializer.Deserialize<ChatResponse>(json)!.ResolvedQuestion);
    }

    [Fact]
    public void Chat_response_reads_intent_scores_and_ranked_hits()
    {
        const string json = """
        {"answer":"a","intent":"coverage_question","citations":[],"session_id":"s",
         "intent_confidence":0.93,"intent_model":"tfidf_lr","intent_scores":{"coverage_question":0.93,"out_of_scope":0.07},
         "intent_features":[{"term":"waiting period","weight":0.47}],"search_query":"waiting period Health Gold","search_filter":{"product":"Health","tier":"Gold"},
         "retriever":"azure","retrieved":[{"source_id":"POL-HEALTH-GOLD","clause_id":"CL-WAIT-02","version":"v2","text":"t","score":3.41,"used":true}]}
        """;
        var r = JsonSerializer.Deserialize<ChatResponse>(json)!;
        Assert.Equal(0.93, r.IntentScores!["coverage_question"]);
        Assert.Equal("azure", r.Retriever);
        Assert.True(r.Retrieved![0].Used);
        Assert.Equal(3.41, r.Retrieved[0].Score);
        Assert.Equal("waiting period", r.IntentFeatures![0].Term);
        Assert.Equal("Gold", r.SearchFilter!["tier"]);
        Assert.Equal("waiting period Health Gold", r.SearchQuery);
    }

    [Fact]
    public void Old_chat_json_without_scores_still_reads()
    {
        const string json = """{"answer":"a","intent":"x","citations":[],"session_id":"s"}""";
        var r = JsonSerializer.Deserialize<ChatResponse>(json)!;
        Assert.Null(r.IntentScores);
        Assert.Null(r.Retrieved);
    }
}
