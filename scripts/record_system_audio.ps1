param(
    [Parameter(Mandatory = $true)]
    [string]$OutputPath,

    [int]$Seconds = 0,

    [string]$StopFile = "",

    [ValidateSet("Console", "Multimedia", "Communications")]
    [string]$Role = "Multimedia"
)

$ErrorActionPreference = "Stop"

if ($Seconds -le 0 -and [string]::IsNullOrWhiteSpace($StopFile)) {
    throw "Either -Seconds or -StopFile must be provided."
}

$source = @"
using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;

namespace EchoScribeRecorder
{
    enum EDataFlow { eRender = 0, eCapture = 1, eAll = 2 }
    enum ERole { eConsole = 0, eMultimedia = 1, eCommunications = 2 }
    enum AUDCLNT_SHAREMODE { AUDCLNT_SHAREMODE_SHARED = 0, AUDCLNT_SHAREMODE_EXCLUSIVE = 1 }
    [Flags] enum AudioClientStreamFlags : uint { None = 0, Loopback = 0x00020000 }
    [Flags] enum AudioClientBufferFlags : uint { None = 0, DataDiscontinuity = 0x1, Silent = 0x2, TimestampError = 0x4 }

    [StructLayout(LayoutKind.Sequential, Pack = 2)]
    struct WaveFormatEx
    {
        public ushort wFormatTag;
        public ushort nChannels;
        public uint nSamplesPerSec;
        public uint nAvgBytesPerSec;
        public ushort nBlockAlign;
        public ushort wBitsPerSample;
        public ushort cbSize;
    }

    [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")]
    class MMDeviceEnumerator { }

    [ComImport, Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDeviceEnumerator
    {
        int EnumAudioEndpoints(EDataFlow dataFlow, uint dwStateMask, out IntPtr ppDevices);
        int GetDefaultAudioEndpoint(EDataFlow dataFlow, ERole role, out IMMDevice ppEndpoint);
        int GetDevice([MarshalAs(UnmanagedType.LPWStr)] string pwstrId, out IMMDevice ppDevice);
        int RegisterEndpointNotificationCallback(IntPtr pClient);
        int UnregisterEndpointNotificationCallback(IntPtr pClient);
    }

    [ComImport, Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDevice
    {
        int Activate(ref Guid iid, uint dwClsCtx, IntPtr pActivationParams, out IntPtr ppInterface);
        int OpenPropertyStore(uint stgmAccess, out IntPtr ppProperties);
        int GetId([MarshalAs(UnmanagedType.LPWStr)] out string ppstrId);
        int GetState(out uint pdwState);
    }

    [ComImport, Guid("1CB9AD4C-DBFA-4c32-B178-C2F568A703B2"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IAudioClient
    {
        int Initialize(AUDCLNT_SHAREMODE ShareMode, AudioClientStreamFlags StreamFlags, long hnsBufferDuration, long hnsPeriodicity, IntPtr pFormat, ref Guid AudioSessionGuid);
        int GetBufferSize(out uint pNumBufferFrames);
        int GetStreamLatency(out long phnsLatency);
        int GetCurrentPadding(out uint pNumPaddingFrames);
        int IsFormatSupported(AUDCLNT_SHAREMODE ShareMode, IntPtr pFormat, out IntPtr ppClosestMatch);
        int GetMixFormat(out IntPtr ppDeviceFormat);
        int GetDevicePeriod(out long phnsDefaultDevicePeriod, out long phnsMinimumDevicePeriod);
        int Start();
        int Stop();
        int Reset();
        int SetEventHandle(IntPtr eventHandle);
        int GetService(ref Guid riid, out IntPtr ppv);
    }

    [ComImport, Guid("C8ADBD64-E71E-48a0-A4DE-185C395CD317"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IAudioCaptureClient
    {
        int GetBuffer(out IntPtr ppData, out uint pNumFramesToRead, out AudioClientBufferFlags pdwFlags, out long pu64DevicePosition, out long pu64QPCPosition);
        int ReleaseBuffer(uint NumFramesRead);
        int GetNextPacketSize(out uint pNumFramesInNextPacket);
    }

    public static class Recorder
    {
        const uint CLSCTX_ALL = 23;
        static void Check(int hr) { if (hr < 0) Marshal.ThrowExceptionForHR(hr); }
        public static void Record(string outputPath, int seconds, string stopFile, string roleName)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outputPath)));
            var enumerator = (IMMDeviceEnumerator)(new MMDeviceEnumerator());
            IMMDevice device;
            ERole role = ERole.eMultimedia;
            if (String.Equals(roleName, "Console", StringComparison.OrdinalIgnoreCase)) role = ERole.eConsole;
            if (String.Equals(roleName, "Communications", StringComparison.OrdinalIgnoreCase)) role = ERole.eCommunications;
            Check(enumerator.GetDefaultAudioEndpoint(EDataFlow.eRender, role, out device));

            Guid audioClientId = new Guid("1CB9AD4C-DBFA-4c32-B178-C2F568A703B2");
            IntPtr audioClientPtr;
            Check(device.Activate(ref audioClientId, CLSCTX_ALL, IntPtr.Zero, out audioClientPtr));
            var audioClient = (IAudioClient)Marshal.GetObjectForIUnknown(audioClientPtr);
            Marshal.Release(audioClientPtr);

            IntPtr fmtPtr;
            Check(audioClient.GetMixFormat(out fmtPtr));
            var fmt = (WaveFormatEx)Marshal.PtrToStructure(fmtPtr, typeof(WaveFormatEx));
            int fmtSize = 18 + fmt.cbSize;
            byte[] fmtBytes = new byte[fmtSize];
            Marshal.Copy(fmtPtr, fmtBytes, 0, fmtSize);

            Guid session = Guid.Empty;
            Check(audioClient.Initialize(AUDCLNT_SHAREMODE.AUDCLNT_SHAREMODE_SHARED, AudioClientStreamFlags.Loopback, 10000000, 0, fmtPtr, ref session));

            Guid captureClientId = new Guid("C8ADBD64-E71E-48a0-A4DE-185C395CD317");
            IntPtr capturePtr;
            Check(audioClient.GetService(ref captureClientId, out capturePtr));
            var captureClient = (IAudioCaptureClient)Marshal.GetObjectForIUnknown(capturePtr);
            Marshal.Release(capturePtr);

            using (var fs = new FileStream(outputPath, FileMode.Create, FileAccess.ReadWrite, FileShare.Read))
            {
                WriteWaveHeader(fs, fmtBytes, 0);
                long dataBytes = 0;
                byte[] silence = new byte[fmt.nBlockAlign * 4096];
                DateTime end = seconds > 0 ? DateTime.UtcNow.AddSeconds(seconds) : DateTime.MaxValue;
                Check(audioClient.Start());
                try
                {
                    while (DateTime.UtcNow < end && (String.IsNullOrWhiteSpace(stopFile) || !File.Exists(stopFile)))
                    {
                        uint packetFrames;
                        Check(captureClient.GetNextPacketSize(out packetFrames));
                        if (packetFrames == 0) { Thread.Sleep(10); continue; }
                        while (packetFrames > 0)
                        {
                            IntPtr dataPtr;
                            uint frames;
                            AudioClientBufferFlags flags;
                            long devicePosition, qpcPosition;
                            Check(captureClient.GetBuffer(out dataPtr, out frames, out flags, out devicePosition, out qpcPosition));
                            int bytes = checked((int)(frames * fmt.nBlockAlign));
                            if ((flags & AudioClientBufferFlags.Silent) == AudioClientBufferFlags.Silent)
                            {
                                int remaining = bytes;
                                while (remaining > 0)
                                {
                                    int chunk = Math.Min(remaining, silence.Length);
                                    fs.Write(silence, 0, chunk);
                                    remaining -= chunk;
                                }
                            }
                            else
                            {
                                byte[] buffer = new byte[bytes];
                                Marshal.Copy(dataPtr, buffer, 0, bytes);
                                fs.Write(buffer, 0, bytes);
                            }
                            dataBytes += bytes;
                            Check(captureClient.ReleaseBuffer(frames));
                            Check(captureClient.GetNextPacketSize(out packetFrames));
                        }
                    }
                }
                finally
                {
                    audioClient.Stop();
                    Marshal.FreeCoTaskMem(fmtPtr);
                }
                fs.Position = 0;
                WriteWaveHeader(fs, fmtBytes, dataBytes);
            }
        }

        static void WriteWaveHeader(Stream s, byte[] fmtBytes, long dataBytes)
        {
            using (var bw = new BinaryWriter(s, System.Text.Encoding.ASCII, true))
            {
                bw.Write(System.Text.Encoding.ASCII.GetBytes("RIFF"));
                bw.Write((uint)(4 + 8 + fmtBytes.Length + 8 + dataBytes));
                bw.Write(System.Text.Encoding.ASCII.GetBytes("WAVE"));
                bw.Write(System.Text.Encoding.ASCII.GetBytes("fmt "));
                bw.Write((uint)fmtBytes.Length);
                bw.Write(fmtBytes);
                bw.Write(System.Text.Encoding.ASCII.GetBytes("data"));
                bw.Write((uint)dataBytes);
            }
        }
    }
}
"@

Add-Type -TypeDefinition $source
[EchoScribeRecorder.Recorder]::Record($OutputPath, $Seconds, $StopFile, $Role)
Write-Host "Recorded system audio to $OutputPath"

