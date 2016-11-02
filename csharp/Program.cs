using System;

namespace Sedna
{
    public class Program
    {
        public static void Main(string[] args)
        {
            Errors.Add(new Error(){Code = "E0001" ,EClass = ErrorLevel.Warning, Message = "This is a warning", Pos = 1, Line = 10} );
            
            if(Errors.HasErrors())
            {
                Errors.Print();
                Console.ReadKey();
            }
            
        }
    }
}
