# Test environment only: caller must pass the handle of its own newly launched AIR child.
# No enumeration, priority/affinity changes, or machine power-plan changes.
if (-not ('ContinuousSceneTest.Power' -as [type])) {
Add-Type -TypeDefinition @'
using System;
using System.Diagnostics;
using System.ComponentModel;
using System.Runtime.InteropServices;
namespace ContinuousSceneTest {
 public static class Power {
  [StructLayout(LayoutKind.Sequential)] public struct State { public uint Version, ControlMask, StateMask; }
  [DllImport("kernel32.dll", SetLastError=true)] static extern bool GetProcessInformation(IntPtr p, int kind, ref State s, uint size);
  [DllImport("kernel32.dll", SetLastError=true)] static extern bool SetProcessInformation(IntPtr p, int kind, ref State s, uint size);
  public static State Read(Process p) {
   var s = new State {Version=1};
   if (!GetProcessInformation(p.Handle,4,ref s,12)) throw new Win32Exception(Marshal.GetLastWin32Error());
   return s;
  }
  public static void Write(Process p, State s) {
   if (!SetProcessInformation(p.Handle,4,ref s,12)) throw new Win32Exception(Marshal.GetLastWin32Error());
  }
  public static State Responsive(Process p) {
   var s=Read(p); s.ControlMask|=1; s.StateMask&=~1u; Write(p,s);
   s=Read(p);
   if ((s.ControlMask&1)==0 || (s.StateMask&1)!=0) throw new InvalidOperationException("HighQoS readback failed");
   return s;
  }
 }
}
'@
}
