namespace Saathi.Client;

public class ApiResult<T>
{
    public bool Success { get; init; }
    public T? Data { get; init; }
    public string? Error { get; init; }

    public static ApiResult<T> Ok(T data) => new() { Success = true, Data = data };
    public static ApiResult<T> Fail(string error) => new() { Success = false, Error = error };
}

public class SaathiApiException : Exception
{
    public int StatusCode { get; }

    public SaathiApiException(string message, int statusCode) : base(message)
    {
        StatusCode = statusCode;
    }
}