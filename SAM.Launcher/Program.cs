using System;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;

namespace SAM.Launcher;

/// <summary>
/// Starts app\SAM.exe with the same arguments (e.g. an app ID) and exits. The actual program then runs from
/// the subfolder; game windows and the restart after a language change start app\SAM.exe directly.
/// </summary>
internal static class Program
{
    private const uint IconError = 0x10;

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    private static extern int MessageBoxW(IntPtr owner, string text, string caption, uint type);

    private static int Main(string[] args)
    {
        var target = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "app", "SAM.exe");

        if (!File.Exists(target))
        {
            MessageBoxW(IntPtr.Zero, "app\\SAM.exe was not found next to this file.\n\n" + target + "\n\nPlease extract the complete folder.", "Steam Achievement Manager", IconError);
            return 1;
        }

        try
        {
            var start = new ProcessStartInfo(target, string.Join(" ", args.Select(Quote)))
            {
                UseShellExecute = false,
                WorkingDirectory = Path.GetDirectoryName(target),
            };
            Process.Start(start)?.Dispose();
            return 0;
        }
        catch (Win32Exception e)
        {
            MessageBoxW(IntPtr.Zero, e.Message + "\n\n" + target, "Steam Achievement Manager", IconError);
            return 1;
        }
    }

    /// <summary>Quotes an argument following the rules of CommandLineToArgvW.</summary>
    private static string Quote(string argument)
    {
        if (argument.Length > 0 && argument.IndexOfAny(new[] { ' ', '\t', '"' }) < 0)
        {
            return argument;
        }

        var builder = new StringBuilder("\"");
        var backslashes = 0;

        foreach (var c in argument)
        {
            if (c == '\\')
            {
                backslashes++;
                continue;
            }

            builder.Append('\\', c == '"' ? backslashes * 2 + 1 : backslashes);
            builder.Append(c);
            backslashes = 0;
        }

        builder.Append('\\', backslashes * 2);
        return builder.Append('"').ToString();
    }
}
