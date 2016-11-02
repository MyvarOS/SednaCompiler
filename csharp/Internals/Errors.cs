using System;
using System.Collections.Generic;

namespace Sedna
{
    public static class Errors
    {

        private static List<Error> ErrorsIndex { get; set; } = new List<Error>();

        public static void Add(Error e)
        {
            ErrorsIndex.Add(e);
        }

        public static bool HasErrors() => ErrorsIndex.Count != 0;
        public static void Print()
        {
            foreach(var i in ErrorsIndex)
            {
                Console.Write("[");
                switch(i.EClass)
                {
                    case ErrorLevel.Simple:
                        Console.ForegroundColor = ConsoleColor.Green;
                        Console.Write("Simple");
                    break;
                    case ErrorLevel.Warning:
                        Console.ForegroundColor = ConsoleColor.Yellow;
                        Console.Write("Warning");
                    break;
                    case ErrorLevel.Critical:
                        Console.ForegroundColor = ConsoleColor.Red;
                        Console.Write("Critical");
                    break;
                }

                Console.ResetColor();
                Console.Write("]|");
                Console.ForegroundColor = ConsoleColor.DarkYellow;
                Console.Write(i.Code);
                Console.ResetColor();
                Console.Write("| ");
                Console.Write(i.Message + " ");
                Console.ForegroundColor = ConsoleColor.Cyan;
                Console.Write("(");
                Console.ResetColor();
                Console.Write(i.Line + "-" + i.Pos);
                Console.ForegroundColor = ConsoleColor.Cyan;
                Console.WriteLine(")");
                Console.ResetColor();

            }
        }
    }
}