using System;
using System.Collections.Generic;
using System.IO;

namespace Sedna
{
    public class Compiler
    {
        public void Compile(List<string> src)
        {
            foreach(var i in src)
            {
                var ast = Parser.Parse(File.ReadAllText(i));//read src file and parse it

                if(Errors.HasErrors()) //stop parsing no point in parsing code that is broken
                {
                    Errors.Print();
                    Environment.Exit(1); //exit with error
                }
            }
        }
    }
}