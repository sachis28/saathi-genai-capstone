// Saathi.Client is the C# library the web app and console use to talk to the Python API.
namespace Saathi.Client;

// Wraps every API call: either Success with Data, or a readable Error. The UI never has to catch exceptions.
public class ApiResult<T>
{
    public bool Success { get; init; }
    public T? Data { get; init; }
    public string? Error { get; init; }

    // Small helpers so callers can write ApiResult<T>.Ok(data) or ApiResult<T>.Fail("message").
    public static ApiResult<T> Ok(T data) => new() { Success = true, Data = data };
    public static ApiResult<T> Fail(string error) => new() { Success = false, Error = error };
}

// Thrown inside the HTTP client when the API returns an error status; turned into ApiResult.Fail.
public class SaathiApiException : Exception
{
    public int StatusCode { get; }

    public SaathiApiException(string message, int statusCode) : base(message)
    {
        StatusCode = statusCode;
    }
}