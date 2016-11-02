namespace Sedna
{
    public class Error
    {
        public string Code { get; set; }
        public string Message { get; set; }
        public int Line { get ; set ; }
        public int Pos { get; set; }
        public ErrorLevel EClass { get ; set; }
    }

    public enum ErrorLevel
    {
        Simple,
        Warning,
        Critical
    }
}
