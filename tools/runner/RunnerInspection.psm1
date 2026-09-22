Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Read-InspectionJson {
    param([string]$Path)
    $observation = Get-InspectionPathObservation $Path
    if ($observation.status -ne 'present') { throw 'invalid_input' }
    $item = $observation.item
    if ($item.Length -gt 262144) { throw 'invalid_input' }
    $text = [IO.File]::ReadAllText($item.FullName, [Text.UTF8Encoding]::new($false, $true))
    $value = ConvertFrom-Json -InputObject $text -AsHashtable -Depth 20
    if ($value -isnot [System.Collections.IDictionary]) { throw 'invalid_input' }
    return $value
}

function Assert-InspectionKeys {
    param($Value, [string[]]$Required, [string[]]$Optional = @())
    if ($Value -isnot [System.Collections.IDictionary]) { throw 'invalid_object' }
    foreach ($key in $Required) { if (-not $Value.Contains($key)) { throw 'missing_field' } }
    foreach ($key in $Value.Keys) { if ($key -cnotin ($Required + $Optional)) { throw 'unknown_field' } }
}

function Assert-InspectionString {
    param($Value, [string]$Pattern)
    if ($Value -isnot [string] -or $Value -cnotmatch $Pattern) { throw 'invalid_string' }
}

function Assert-InspectionInteger {
    param($Value, [long]$Minimum = 0)
    if (($Value -isnot [int] -and $Value -isnot [long]) -or $Value -lt $Minimum) {
        throw 'invalid_integer'
    }
}

function Assert-InspectionBoolean {
    param($Value)
    if ($Value -isnot [bool]) { throw 'invalid_boolean' }
}

function Read-InspectionProfile {
    param([string]$Path)
    if ([string]::IsNullOrWhiteSpace($Path)) { return $null }
    $value = Read-InspectionJson $Path
    Assert-InspectionKeys $value @('schemaVersion', 'profileId', 'repository', 'repositoryId', 'runnerId',
        'serviceName', 'expectedServiceSid', 'runnerRoot', 'minimumFreeBytes', 'requiredTools') @('remoteCliPath')
    if ($value.schemaVersion -cne '1.0') { throw 'invalid_version' }
    Assert-InspectionString $value.profileId '\A[a-z][a-z0-9-]{0,63}\z'
    Assert-InspectionString $value.repository '\A[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*\z'
    Assert-InspectionString $value.serviceName '\Aactions\.runner\.[A-Za-z0-9_.-]+\z'
    Assert-InspectionString $value.expectedServiceSid '\AS-1-\d+(?:-\d+)+\z'
    Assert-InspectionInteger $value.runnerId 1
    Assert-InspectionInteger $value.repositoryId 1
    Assert-InspectionInteger $value.minimumFreeBytes 1
    foreach ($pathKey in @('runnerRoot', 'remoteCliPath')) {
        if ($value.Contains($pathKey)) {
            Assert-InspectionString $value[$pathKey] '\A[^\x00-\x1f]+\z'
            if (-not [IO.Path]::IsPathFullyQualified($value[$pathKey])) { throw 'absolute_path_required' }
        }
    }
    if ($value.requiredTools -isnot [array] -or $value.requiredTools.Count -eq 0 -or
        $value.requiredTools.Count -gt 3) { throw 'invalid_tools' }
    $names = @()
    foreach ($tool in $value.requiredTools) {
        Assert-InspectionKeys $tool @('name', 'path', 'expectedVersion')
        if ($tool.name -cnotin @('git', 'python', 'pwsh') -or $tool.name -cin $names) { throw 'invalid_tool' }
        $names += $tool.name
        Assert-InspectionString $tool.path '\A[^\x00-\x1f]+\z'
        if (-not [IO.Path]::IsPathFullyQualified($tool.path)) { throw 'absolute_path_required' }
        Assert-InspectionString $tool.expectedVersion '\A\d+\.\d+\.\d+(?:\.windows\.\d+)?\z'
    }
    return $value
}

function Get-InspectionDriveType {
    param([string]$Root)
    # DriveType uses the drive root, without opening a file on a mapped share.
    return [int][IO.DriveInfo]::new($Root).DriveType
}

function Get-InspectionPathObservation {
    param([string]$Path, [bool]$RequireDirectory = $false)
    try {
        if ([string]::IsNullOrWhiteSpace($Path) -or $Path -match '[\x00-\x1f]') {
            throw 'invalid_path'
        }
        if ($IsWindows) {
            # Reject UNC, device and provider paths before any metadata access. A
            # relative JSON input remains relative to the current local filesystem.
            if ($Path -notmatch '\A[A-Za-z]:[\\/]') {
                if ($Path -match '\A[\\/]|:') { throw 'local_path_required' }
                $location = Get-Location
                if ($location.Provider.Name -cne 'FileSystem') { throw 'local_path_required' }
                $Path = $location.ProviderPath.TrimEnd('\', '/') + '\' + $Path
            }
            $Path = $Path.Replace('/', '\')
            if ($Path -notmatch '\A[A-Za-z]:\\' -or $Path.Substring(2) -match '[<>:"|?*]') {
                throw 'local_path_required'
            }
            $root = $Path.Substring(0, 3)
            $parts = @($Path.Substring(3).Split('\', [StringSplitOptions]::RemoveEmptyEntries))
            foreach ($part in $parts) {
                if ($part -eq '..' -or ($part -ne '.' -and ($part -match '[. ]\z' -or
                    $part -match '\A(?:CON|PRN|AUX|NUL|CONIN\$|CONOUT\$|(?:COM|LPT)[1-9\u00b9\u00b2\u00b3])(?:\.|\z)'))) {
                    throw 'invalid_path'
                }
            }
            if ((Get-InspectionDriveType $root) -notin @(2, 3, 5, 6)) { throw 'local_drive_required' }
            # Get-Item resolves PSDrive names, while DriveInfo uses native OS drive
            # names. Refuse a process-local alias before it can redirect metadata.
            try {
                $drive = @(Get-PSDrive -Name $root.Substring(0, 1) -PSProvider FileSystem -ErrorAction Stop)
            } catch { throw 'native_drive_binding_required' }
            if ($drive.Count -ne 1 -or
                -not [StringComparer]::OrdinalIgnoreCase.Equals($drive[0].Root, $root)) {
                throw 'native_drive_binding_required'
            }
            $separator = '\'
        }
        else {
            # POSIX paths are needed by synthetic PowerShell tests; no live native
            # collection is enabled on these platforms.
            if ($Path.Contains(':') -or $Path.StartsWith('\')) { throw 'local_path_required' }
            if (-not $Path.StartsWith('/')) {
                $location = Get-Location
                if ($location.Provider.Name -cne 'FileSystem') { throw 'local_path_required' }
                $Path = $location.ProviderPath.TrimEnd('/') + '/' + $Path
            }
            $root = '/'
            $parts = @($Path.Substring(1).Split('/', [StringSplitOptions]::RemoveEmptyEntries))
            if ('..' -cin $parts) { throw 'invalid_path' }
            $separator = '/'
        }
        $paths = [Collections.Generic.List[string]]::new()
        $paths.Add($root)
        $current = $root.TrimEnd($separator)
        foreach ($part in $parts) {
            if ($part -eq '.') { continue }
            $current += $separator + $part
            $paths.Add($current)
        }
        for ($index = 0; $index -lt $paths.Count; $index++) {
            # Inspect each parent before touching a child. Reading leaf metadata
            # first would already follow a junction, potentially onto a network.
            $item = Get-Item -LiteralPath $paths[$index] -Force -ErrorAction Stop
            if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
                return @{ status = 'reparse'; item = $null }
            }
            if ($index -lt $paths.Count - 1 -and -not $item.PSIsContainer) {
                return @{ status = 'wrong_type'; item = $null }
            }
        }
        if ($item.PSIsContainer -ne $RequireDirectory) { return @{ status = 'wrong_type'; item = $null } }
        return @{ status = 'present'; item = $item }
    }
    catch [UnauthorizedAccessException] { return @{ status = 'access_denied'; item = $null } }
    catch [System.Management.Automation.ItemNotFoundException] { return @{ status = 'not_found'; item = $null } }
    catch {
        if ($_.CategoryInfo.Category -eq 'PermissionDenied') { return @{ status = 'access_denied'; item = $null } }
        return @{ status = 'unknown'; item = $null }
    }
}

function Get-InspectionPathState {
    param([string]$Path, [bool]$RequireDirectory = $false)
    return (Get-InspectionPathObservation $Path $RequireDirectory).status
}

function Invoke-InspectionNative {
    param([string]$Path, [string[]]$Arguments, [bool]$UseAuthentication = $false)
    try {
        if (-not $IsWindows) { return @{ status = 'unavailable'; output = ''; cleanupConfirmed = $false } }
        if ((Get-InspectionPathState $Path) -ne 'present') { throw 'unavailable' }
        Initialize-InspectionNative
        $environment = [Collections.Generic.Dictionary[string, string]]::new([StringComparer]::OrdinalIgnoreCase)
        if (-not $UseAuthentication) {
            $environment['SystemRoot'] = [Environment]::GetEnvironmentVariable('SystemRoot')
            $environment['PATH'] = [Environment]::SystemDirectory
        }
        else {
            foreach ($entry in [Environment]::GetEnvironmentVariables().GetEnumerator()) {
                $environment[[string]$entry.Key] = [string]$entry.Value
            }
            $environment['GH_PROMPT_DISABLED'] = '1'
            $environment['GIT_TERMINAL_PROMPT'] = '0'
        }
        $result = [RunnerInspection.NativeProbe]::Run($Path, $Arguments, $environment, 10000)
        return @{ status = $result.Status; output = $result.Output; cleanupConfirmed = $result.CleanupConfirmed }
    }
    catch { return @{ status = 'unavailable'; output = ''; cleanupConfirmed = $false } }
}

function Initialize-InspectionNative {
    if ('RunnerInspection.NativeProbe' -as [type]) { return }
    # A job is assigned while the process is suspended: no start/assignment race.
    # PeekNamedPipe avoids asynchronous stream readers whose Dispose can block.
    Add-Type -TypeDefinition @'
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using System.Text;
using System.Threading;
namespace RunnerInspection {
public sealed class ProbeResult {
 public string Status = "unavailable";
 public string Output = "";
 public bool CleanupConfirmed;
}
public static class NativeProbe {
 [StructLayout(LayoutKind.Sequential)] struct SA { public int Length; public IntPtr Security; [MarshalAs(UnmanagedType.Bool)] public bool Inherit; }
 [StructLayout(LayoutKind.Sequential, CharSet=CharSet.Unicode)] struct SI {
  public int Size; public string Reserved, Desktop, Title; public uint X,Y,XS,YS,XC,YC,Fill,Flags;
  public short Show,ReservedSize; public IntPtr ReservedData,Input,Output,Error;
 }
 [StructLayout(LayoutKind.Sequential)] struct SIX { public SI Start; public IntPtr Attributes; }
 [StructLayout(LayoutKind.Sequential)] struct PI { public IntPtr Process,Thread; public uint Id,ThreadId; }
 [StructLayout(LayoutKind.Sequential)] struct BasicLimit {
  public long ProcessTime,JobTime; public uint Flags; public UIntPtr MinWorking,MaxWorking;
  public uint ActiveLimit; public UIntPtr Affinity; public uint Priority,Scheduling;
 }
 [StructLayout(LayoutKind.Sequential)] struct IO { public ulong RO,WO,OO,RB,WB,OB; }
 [StructLayout(LayoutKind.Sequential)] struct ExtendedLimit { public BasicLimit Basic; public IO Io; public UIntPtr ProcessMemory,JobMemory,PeakProcessMemory,PeakJobMemory; }
 [StructLayout(LayoutKind.Sequential)] struct Accounting { public long User,Kernel,PeriodUser,PeriodKernel; public uint Faults,Total,Active,Terminated; }
 [DllImport("kernel32", SetLastError=true)] static extern IntPtr CreateJobObject(IntPtr security,string name);
 [DllImport("kernel32", SetLastError=true)] static extern bool SetInformationJobObject(IntPtr job,int kind,ref ExtendedLimit info,uint length);
 [DllImport("kernel32", SetLastError=true)] static extern bool QueryInformationJobObject(IntPtr job,int kind,out Accounting info,uint length,IntPtr result);
 [DllImport("kernel32", SetLastError=true)] static extern bool AssignProcessToJobObject(IntPtr job,IntPtr process);
 [DllImport("kernel32", SetLastError=true)] static extern bool TerminateJobObject(IntPtr job,uint code);
 [DllImport("kernel32", SetLastError=true)] static extern bool TerminateProcess(IntPtr process,uint code);
 [DllImport("kernel32", SetLastError=true)] static extern bool CloseHandle(IntPtr handle);
 [DllImport("kernel32", SetLastError=true)] static extern bool CreatePipe(out IntPtr read,out IntPtr write,ref SA security,uint size);
 [DllImport("kernel32", SetLastError=true)] static extern bool SetHandleInformation(IntPtr handle,uint mask,uint flags);
 [DllImport("kernel32", CharSet=CharSet.Unicode, SetLastError=true)] static extern IntPtr CreateFile(string name,uint access,uint share,ref SA security,uint creation,uint flags,IntPtr template);
 [DllImport("kernel32", SetLastError=true)] static extern bool InitializeProcThreadAttributeList(IntPtr list,int count,int flags,ref IntPtr size);
 [DllImport("kernel32", SetLastError=true)] static extern bool UpdateProcThreadAttribute(IntPtr list,uint flags,IntPtr attribute,IntPtr value,IntPtr size,IntPtr previous,IntPtr returned);
 [DllImport("kernel32")] static extern void DeleteProcThreadAttributeList(IntPtr list);
 [DllImport("kernel32", CharSet=CharSet.Unicode, SetLastError=true)] static extern bool CreateProcess(string app,StringBuilder command,IntPtr processSecurity,IntPtr threadSecurity,bool inherit,uint flags,IntPtr environment,string directory,ref SIX startup,out PI process);
 [DllImport("kernel32", SetLastError=true)] static extern uint ResumeThread(IntPtr thread);
 [DllImport("kernel32", SetLastError=true)] static extern uint WaitForSingleObject(IntPtr handle,uint time);
 [DllImport("kernel32", SetLastError=true)] static extern bool GetExitCodeProcess(IntPtr process,out uint code);
 [DllImport("kernel32", SetLastError=true)] static extern bool PeekNamedPipe(IntPtr pipe,IntPtr buffer,uint size,IntPtr read,out uint available,IntPtr left);
 [DllImport("kernel32", SetLastError=true)] static extern bool ReadFile(IntPtr file,byte[] buffer,uint count,out uint read,IntPtr overlapped);
 static void Require(bool value) { if(!value) throw new InvalidOperationException("native_probe_failed"); }
 static void Close(ref IntPtr handle) { if(handle!=IntPtr.Zero && handle!=new IntPtr(-1)) CloseHandle(handle); handle=IntPtr.Zero; }
 static string Quote(string value) {
  var text=new StringBuilder("\""); int slashes=0;
  foreach(char c in value) { if(c=='\\') {slashes++;continue;} if(c=='\"') text.Append('\\',slashes*2+1); else text.Append('\\',slashes); text.Append(c);slashes=0; }
  text.Append('\\',slashes*2); return text.Append('"').ToString();
 }
 static uint Active(IntPtr job) { Accounting value; Require(QueryInformationJobObject(job,1,out value,(uint)Marshal.SizeOf<Accounting>(),IntPtr.Zero)); return value.Active; }
 static bool Drain(IntPtr pipe,MemoryStream bytes) {
  uint available;
  if(!PeekNamedPipe(pipe,IntPtr.Zero,0,IntPtr.Zero,out available,IntPtr.Zero)) {
   if(Marshal.GetLastWin32Error()==109) return true;
   throw new InvalidOperationException("pipe_probe_failed");
  }
  if(available==0) return false;
  uint count=Math.Min(available,(uint)(65537-bytes.Length));
  var buffer=new byte[count]; uint read;
  Require(ReadFile(pipe,buffer,count,out read,IntPtr.Zero)); bytes.Write(buffer,0,(int)read);
  if(bytes.Length>65536) throw new InvalidDataException("oversize");
  return false;
 }
 public static ProbeResult Run(string path,string[] arguments,IDictionary<string,string> environment,int timeoutMs) {
  var result=new ProbeResult(); var watch=Stopwatch.StartNew();
  IntPtr job=IntPtr.Zero,or=IntPtr.Zero,ow=IntPtr.Zero,er=IntPtr.Zero,ew=IntPtr.Zero,input=IntPtr.Zero,attrs=IntPtr.Zero,handles=IntPtr.Zero,env=IntPtr.Zero;
  PI process=new PI(); bool assigned=false,attributesReady=false;
  using(var stdout=new MemoryStream()) using(var stderr=new MemoryStream()) {
   try {
    job=CreateJobObject(IntPtr.Zero,null);Require(job!=IntPtr.Zero);
    var limits=new ExtendedLimit(); limits.Basic.Flags=0x2000;
    Require(SetInformationJobObject(job,9,ref limits,(uint)Marshal.SizeOf<ExtendedLimit>()));
    var sa=new SA {Length=Marshal.SizeOf<SA>(),Security=IntPtr.Zero,Inherit=true};
    Require(CreatePipe(out or,out ow,ref sa,0));Require(SetHandleInformation(or,1,0));
    Require(CreatePipe(out er,out ew,ref sa,0));Require(SetHandleInformation(er,1,0));
    input=CreateFile("NUL",0x80000000,3,ref sa,3,0,IntPtr.Zero);Require(input!=new IntPtr(-1));
    IntPtr size=IntPtr.Zero;InitializeProcThreadAttributeList(IntPtr.Zero,1,0,ref size);
    attrs=Marshal.AllocHGlobal(size);Require(InitializeProcThreadAttributeList(attrs,1,0,ref size));attributesReady=true;
    handles=Marshal.AllocHGlobal(3*IntPtr.Size);
    Marshal.WriteIntPtr(handles,0,input);Marshal.WriteIntPtr(handles,IntPtr.Size,ow);Marshal.WriteIntPtr(handles,2*IntPtr.Size,ew);
    Require(UpdateProcThreadAttribute(attrs,0,new IntPtr(0x20002),handles,new IntPtr(3*IntPtr.Size),IntPtr.Zero,IntPtr.Zero));
    var startup=new SIX();startup.Start.Size=Marshal.SizeOf<SIX>();startup.Start.Flags=0x100;
    startup.Start.Input=input;startup.Start.Output=ow;startup.Start.Error=ew;startup.Attributes=attrs;
    var block=String.Join("\0",environment.OrderBy(x=>x.Key,StringComparer.OrdinalIgnoreCase).Select(x=>x.Key+"="+x.Value))+"\0\0";
    env=Marshal.StringToHGlobalUni(block);
    var command=new StringBuilder(Quote(path));foreach(string arg in arguments)command.Append(' ').Append(Quote(arg));
    Require(CreateProcess(path,command,IntPtr.Zero,IntPtr.Zero,true,0x08080404,env,Path.GetDirectoryName(path),ref startup,out process));
    Require(AssignProcessToJobObject(job,process.Process));assigned=true;
    Require(ResumeThread(process.Thread)!=UInt32.MaxValue);
    Close(ref ow);Close(ref ew);Close(ref input);
    while(watch.ElapsedMilliseconds<timeoutMs) {
     bool outDone=Drain(or,stdout),errDone=Drain(er,stderr);
     if(WaitForSingleObject(process.Process,0)==0 && Active(job)==0 && outDone && errDone) {
      uint code;Require(GetExitCodeProcess(process.Process,out code));
      result.Status=code==0 ? "observed" : "nonzero";
      if(code==0)result.Output=new UTF8Encoding(false,true).GetString(stdout.ToArray());
      break;
     }
     Thread.Sleep(10);
    }
    if(result.Status=="unavailable")result.Status="timeout";
   } catch(InvalidDataException) {result.Status="oversize";result.Output="";}
   catch {result.Status="unavailable";result.Output="";}
   finally {
    // Only this job's descendants can be terminated, including after parent exit.
    if(job!=IntPtr.Zero && assigned) {
     TerminateJobObject(job,124);
     try {while(watch.ElapsedMilliseconds<timeoutMs+2000 && Active(job)>0)Thread.Sleep(10);result.CleanupConfirmed=Active(job)==0;} catch {result.CleanupConfirmed=false;}
    } else if(process.Process!=IntPtr.Zero) {
     TerminateProcess(process.Process,124);
     result.CleanupConfirmed=WaitForSingleObject(process.Process,2000)==0;
    }
    if(!result.CleanupConfirmed) {result.Status="unavailable";result.Output="";}
    Close(ref process.Thread);Close(ref process.Process);Close(ref input);Close(ref ow);Close(ref ew);Close(ref or);Close(ref er);Close(ref job);
    if(attributesReady)DeleteProcThreadAttributeList(attrs);
    if(attrs!=IntPtr.Zero)Marshal.FreeHGlobal(attrs);if(handles!=IntPtr.Zero)Marshal.FreeHGlobal(handles);if(env!=IntPtr.Zero)Marshal.FreeHGlobal(env);
   }
  }
  return result;
 }
}
}
'@
}

function Get-InspectionIdentity {
    $result = @{ tokenKnown = $false; identitySid = ''; tokenGroupSids = @();
        roleAdministrator = $false; localMembershipKnown = $false; administratorMemberSids = @() }
    $identity = $null
    try {
        $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
        $result.identitySid = $identity.User.Value
        $result.tokenGroupSids = @($identity.Groups | ForEach-Object { $_.Value })
        $result.roleAdministrator = [Security.Principal.WindowsPrincipal]::new($identity).IsInRole(
            [Security.Principal.WindowsBuiltInRole]::Administrator)
        $result.tokenKnown = $true
        $result.administratorMemberSids = @(Get-LocalGroupMember -SID 'S-1-5-32-544' -ErrorAction Stop |
            ForEach-Object { $_.SID.Value })
        $result.localMembershipKnown = $true
    }
    catch { } # Partial evidence remains explicitly unknown; never emit exception text.
    finally { if ($null -ne $identity) { $identity.Dispose() } }
    return $result
}

function Get-InspectionObservations {
    param($Profile, [bool]$CheckRemote)
    $facts = @{
        platform = if ($IsWindows) { 'Windows' } else { 'unsupported' }
        architecture = [Runtime.InteropServices.RuntimeInformation]::OSArchitecture.ToString()
        currentIdentity = Get-InspectionIdentity
        serviceQuery = @{ status = 'unavailable'; services = @() }
        processQuery = @{ status = 'unavailable'; processes = @() }
        runnerRoot = @{ status = 'unknown' }
        registration = @{ status = 'unknown'; runnerId = 0; repository = ''; scope = 'unknown' }
        disk = @{ status = 'unknown'; freeBytes = 0 }
        tools = @()
        remote = @{ status = 'unknown'; registered = $false; private = $false;
            repositoryId = 0; repository = ''; runnerId = 0; online = $false; busy = $false; os = 'unknown' }
    }
    if (-not $IsWindows) { return $facts }
    try {
        $services = @(Get-CimInstance Win32_Service -Filter "Name LIKE 'actions.runner.%'" -ErrorAction Stop)
        $facts.serviceQuery.services = @($services | ForEach-Object {
            $sid = ''
            try {
                $account = [string]$_.StartName
                if ($account.StartsWith('.\', [StringComparison]::Ordinal)) {
                    $account = [Environment]::MachineName + '\' + $account.Substring(2)
                }
                $sid = [Security.Principal.NTAccount]::new($account).Translate(
                    [Security.Principal.SecurityIdentifier]).Value
            } catch { }
            @{ name = [string]$_.Name; state = [string]$_.State; startMode = [string]$_.StartMode;
                processId = [long]$_.ProcessId; accountSid = $sid; executablePath = $(
                    # Official service has one binary and no arguments. Refuse ambiguous paths.
                    if ([string]$_.PathName -cmatch '\A"([^"\r\n]+)"\z') { $Matches[1] }
                    elseif ([string]$_.PathName -cmatch '\A[^"\s]+\.exe\z') { [string]$_.PathName }
                    else { '' }
                ) }
        })
        $facts.serviceQuery.status = 'observed'
    }
    catch { $facts.serviceQuery.status = 'unavailable' }
    try {
        $processes = @(Get-CimInstance Win32_Process -Filter `
            "Name = 'Runner.Listener.exe' OR Name = 'Runner.Worker.exe' OR Name = 'RunnerService.exe'" -ErrorAction Stop)
        $facts.processQuery.processes = @($processes | ForEach-Object {
            $sid = ''
            try {
                $owner = Invoke-CimMethod -InputObject $_ -MethodName GetOwnerSid -ErrorAction Stop
                if ($owner.ReturnValue -eq 0) { $sid = [string]$owner.Sid }
            } catch { }
            @{ name = [string]$_.Name; processId = [long]$_.ProcessId;
                parentProcessId = [long]$_.ParentProcessId; ownerSid = $sid;
                executablePath = [string]$_.ExecutablePath }
        })
        $facts.processQuery.status = 'observed'
    }
    catch { $facts.processQuery.status = 'unavailable' }
    if ($null -eq $Profile) { return $facts }
    $facts.runnerRoot.status = Get-InspectionPathState $Profile.runnerRoot $true
    if ($facts.runnerRoot.status -eq 'present') {
        $registrationPath = Join-Path $Profile.runnerRoot '.runner'
        $registrationState = Get-InspectionPathState $registrationPath
        $facts.registration.status = $registrationState
        if ($registrationState -eq 'present') {
            try {
                # Read only the fixed non-secret registration file, never .credentials*.
                $registration = Read-InspectionJson $registrationPath
                Assert-InspectionInteger $registration.agentId 1
                Assert-InspectionString $registration.gitHubUrl '\Ahttps://github\.com/[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*/?\z'
                $facts.registration = @{ status = 'observed'; runnerId = $registration.agentId;
                    repository = $registration.gitHubUrl.Substring('https://github.com/'.Length).TrimEnd('/'); scope = 'repository' }
            } catch { $facts.registration.status = 'invalid_output' }
        }
    }
    if ($facts.runnerRoot.status -eq 'present') {
        try {
            $root = $Profile.runnerRoot.Replace('/', '\').Substring(0, 3)
            $drive = @(Get-PSDrive -Name $root.Substring(0, 1) -PSProvider FileSystem -ErrorAction Stop)
            if ($drive.Count -eq 1 -and $drive[0].Root -eq $root -and $null -ne $drive[0].Free) {
                $facts.disk = @{ status = 'observed'; freeBytes = [long]$drive[0].Free }
            }
        } catch { }
    }
    foreach ($tool in $Profile.requiredTools) {
        $probe = Invoke-InspectionNative $tool.path @('--version')
        $version = ''
        if ($probe.status -eq 'observed') {
            $prefix = @{ git = 'git version '; python = 'Python '; pwsh = 'PowerShell ' }[$tool.name]
            if ($probe.output -cmatch ('\A' + [regex]::Escape($prefix) +
                '(?<version>\d+\.\d+\.\d+(?:\.windows\.\d+)?)\r?\n?\z')) {
                $version = $Matches.version
            } else { $probe.status = 'invalid_output' }
        }
        $facts.tools += @{ name = $tool.name; status = $probe.status; version = $version }
    }
    if ($CheckRemote -and $Profile.Contains('remoteCliPath')) {
        # Only two fixed GET endpoints. The CLI uses its existing auth without exporting it.
        $repo = Invoke-InspectionNative $Profile.remoteCliPath @('api', '--hostname', 'github.com', '--method', 'GET',
            "repos/$($Profile.repository)", '--jq', '{id:.id,full_name:.full_name,private:.private}') $true
        $runner = Invoke-InspectionNative $Profile.remoteCliPath @('api', '--hostname', 'github.com', '--method', 'GET',
            "repos/$($Profile.repository)/actions/runners/$($Profile.runnerId)", '--jq',
            '{id:.id,os:.os,status:.status,busy:.busy}') $true
        if ($repo.status -eq 'observed' -and $runner.status -eq 'observed') {
            try {
                $repoData = ConvertFrom-Json $repo.output -AsHashtable
                $runnerData = ConvertFrom-Json $runner.output -AsHashtable
                Assert-InspectionBoolean $repoData.private
                Assert-InspectionInteger $repoData.id 1
                Assert-InspectionString $repoData.full_name '\A[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*\z'
                Assert-InspectionBoolean $runnerData.busy
                Assert-InspectionInteger $runnerData.id 1
                Assert-InspectionString $runnerData.os '\A(?:Windows|Linux|OSX)\z'
                Assert-InspectionString $runnerData.status '\A(?:online|offline)\z'
                $facts.remote = @{ status = 'observed'; registered = $true; private = $repoData.private;
                    repositoryId = $repoData.id; repository = $repoData.full_name;
                    runnerId = $runnerData.id; online = $runnerData.status -ceq 'online';
                    busy = $runnerData.busy; os = $runnerData.os }
            } catch { $facts.remote.status = 'invalid_output' }
        } else { $facts.remote.status = 'unavailable' }
    }
    return $facts
}

function Assert-InspectionFacts {
    param($Facts)
    Assert-InspectionKeys $Facts @('platform', 'architecture', 'currentIdentity', 'serviceQuery',
        'processQuery', 'runnerRoot', 'registration', 'disk', 'tools', 'remote')
    Assert-InspectionString $Facts.platform '\A(?:Windows|unsupported)\z'
    Assert-InspectionString $Facts.architecture '\A(?:X64|X86|Arm64|Arm|unknown)\z'
    $identity = $Facts.currentIdentity
    Assert-InspectionKeys $identity @('tokenKnown', 'identitySid', 'tokenGroupSids',
        'roleAdministrator', 'localMembershipKnown', 'administratorMemberSids')
    foreach ($key in @('tokenKnown', 'roleAdministrator', 'localMembershipKnown')) {
        Assert-InspectionBoolean $identity[$key]
    }
    Assert-InspectionString $identity.identitySid '\A(?:S-1-\d+(?:-\d+)+)?\z'
    foreach ($key in @('tokenGroupSids', 'administratorMemberSids')) {
        if ($identity[$key] -isnot [array]) { throw 'invalid_sid_array' }
        foreach ($sid in $identity[$key]) { Assert-InspectionString $sid '\AS-1-\d+(?:-\d+)+\z' }
    }
    foreach ($kind in @('service', 'process')) {
        $query = $Facts[$kind + 'Query']
        $rowsKey = if ($kind -eq 'service') { 'services' } else { 'processes' }
        Assert-InspectionKeys $query @('status', $rowsKey)
        Assert-InspectionString $query.status '\A(?:observed|unavailable|access_denied)\z'
        if ($query[$rowsKey] -isnot [array] -or $query[$rowsKey].Count -gt 100) { throw 'invalid_rows' }
        foreach ($row in $query[$rowsKey]) {
            if ($kind -eq 'service') {
                Assert-InspectionKeys $row @('name', 'state', 'startMode', 'processId', 'accountSid', 'executablePath')
                Assert-InspectionString $row.name '\Aactions\.runner\.[A-Za-z0-9_.-]+\z'
                Assert-InspectionString $row.state '\A(?:Running|Stopped|Paused|Start Pending|Stop Pending|Unknown)\z'
                Assert-InspectionString $row.startMode '\A(?:Auto|Manual|Disabled|Unknown)\z'
                Assert-InspectionString $row.accountSid '\A(?:S-1-\d+(?:-\d+)+)?\z'
            } else {
                Assert-InspectionKeys $row @('name', 'processId', 'parentProcessId', 'ownerSid', 'executablePath')
                Assert-InspectionString $row.name '\ARunner\.(?:Listener|Worker)\.exe\z|\ARunnerService\.exe\z'
                Assert-InspectionInteger $row.parentProcessId
                Assert-InspectionString $row.ownerSid '\A(?:S-1-\d+(?:-\d+)+)?\z'
            }
            Assert-InspectionInteger $row.processId
            Assert-InspectionString $row.executablePath '\A[^\x00-\x1f]*\z'
        }
    }
    Assert-InspectionKeys $Facts.runnerRoot @('status')
    Assert-InspectionString $Facts.runnerRoot.status '\A(?:present|not_found|access_denied|reparse|wrong_type|unknown)\z'
    Assert-InspectionKeys $Facts.registration @('status', 'runnerId', 'repository', 'scope')
    Assert-InspectionString $Facts.registration.status '\A(?:observed|not_found|access_denied|reparse|wrong_type|unknown|invalid_output)\z'
    Assert-InspectionString $Facts.registration.repository '\A(?:[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*)?\z'
    Assert-InspectionString $Facts.registration.scope '\A(?:repository|unknown)\z'
    Assert-InspectionInteger $Facts.registration.runnerId
    Assert-InspectionKeys $Facts.disk @('status', 'freeBytes')
    Assert-InspectionString $Facts.disk.status '\A(?:observed|unknown)\z'
    Assert-InspectionInteger $Facts.disk.freeBytes
    if ($Facts.tools -isnot [array] -or $Facts.tools.Count -gt 3) { throw 'invalid_tools' }
    foreach ($tool in $Facts.tools) {
        Assert-InspectionKeys $tool @('name', 'status', 'version')
        Assert-InspectionString $tool.name '\A(?:git|python|pwsh)\z'
        Assert-InspectionString $tool.status '\A(?:observed|timeout|nonzero|oversize|unavailable|invalid_output)\z'
        Assert-InspectionString $tool.version '\A(?:\d+\.\d+\.\d+(?:\.windows\.\d+)?)?\z'
    }
    Assert-InspectionKeys $Facts.remote @('status', 'registered', 'private', 'repositoryId', 'repository', 'runnerId', 'online', 'busy', 'os')
    Assert-InspectionString $Facts.remote.status '\A(?:observed|unknown|unavailable|invalid_output|access_denied)\z'
    Assert-InspectionString $Facts.remote.os '\A(?:Windows|Linux|OSX|unknown)\z'
    Assert-InspectionInteger $Facts.remote.runnerId
    Assert-InspectionInteger $Facts.remote.repositoryId
    Assert-InspectionString $Facts.remote.repository '\A(?:[A-Za-z0-9][A-Za-z0-9_.-]*/[A-Za-z0-9][A-Za-z0-9_.-]*)?\z'
    foreach ($key in @('registered', 'private', 'online', 'busy')) {
        Assert-InspectionBoolean $Facts.remote[$key]
    }
}

function Test-InspectionExecutablePath {
    param([string]$Observed, [string]$Expected, [bool]$Synthetic)
    try {
        if (-not [IO.Path]::IsPathFullyQualified($Observed) -or
            -not [IO.Path]::GetFullPath($Observed).Equals([IO.Path]::GetFullPath($Expected),
                [StringComparison]::OrdinalIgnoreCase)) { return $false }
        if ($Synthetic) { return $true }
        return (Get-InspectionPathState $Observed) -eq 'present'
    } catch { return $false }
}

function New-InspectionReport {
    param($Profile, $Facts, [bool]$Synthetic, [bool]$PrivateDetails)
    Assert-InspectionFacts $Facts
    $reasons = [Collections.Generic.List[string]]::new()
    $identity = $Facts.currentIdentity
    $identityKnown = $identity.tokenKnown -and $identity.identitySid -ne '' -and
        $identity.tokenGroupSids.Count -gt 0 -and $identity.localMembershipKnown
    $administrator = $identity.roleAdministrator -or
        'S-1-5-32-544' -cin $identity.tokenGroupSids -or
        @($identity.administratorMemberSids | Where-Object {
            $_ -ceq $identity.identitySid -or $_ -cin $identity.tokenGroupSids }).Count -gt 0
    $currentClass = if (-not $identityKnown) { 'unknown' } elseif ($administrator) { 'administrator_member' } else { 'non_administrator' }
    $services = @($Facts.serviceQuery.services)
    # A starting/stopping/paused instance is not evidence of an idle machine.
    $active = @($services | Where-Object state -CNE 'Stopped')
    $processes = @($Facts.processQuery.processes)
    $listeners = @($processes | Where-Object name -CEQ 'Runner.Listener.exe')
    $workers = @($processes | Where-Object name -CEQ 'Runner.Worker.exe')
    $selected = @()
    $serviceIdentityMatches = $false
    $processIdentityMatches = $false
    $observerIsServiceIdentity = $false
    $localInstanceBound = $false
    $state = 'unconfigured'
    $toolsMatch = $false
    if ($Facts.platform -cne 'Windows') { $reasons.Add('PLATFORM_UNSUPPORTED') }
    if ($Facts.architecture -cne 'X64') { $reasons.Add('ARCHITECTURE_UNSUPPORTED') }
    if ($Facts.serviceQuery.status -cne 'observed') { $reasons.Add('SERVICE_OBSERVATION_UNKNOWN') }
    if ($Facts.processQuery.status -cne 'observed') { $reasons.Add('PROCESS_OBSERVATION_UNKNOWN') }
    if ($active.Count -gt 1 -or $listeners.Count -gt 1) { $reasons.Add('MULTIPLE_ACTIVE_INSTANCES') }
    if ($workers.Count -gt 0 -or ($Facts.remote.status -ceq 'observed' -and $Facts.remote.busy)) {
        $reasons.Add('RUNNER_BUSY')
    }
    if ($null -eq $Profile) { $reasons.Add('PROFILE_REQUIRED') }
    else {
        $selected = @($services | Where-Object name -CEQ $Profile.serviceName)
        if ($Facts.serviceQuery.status -cne 'observed' -or $Facts.runnerRoot.status -cin @('access_denied', 'unknown')) {
            $state = 'unknown'
        } elseif ($selected.Count -eq 0 -and $Facts.runnerRoot.status -ceq 'not_found') {
            $state = 'not_installed'
        } elseif ($selected.Count -ne 1 -or $Facts.runnerRoot.status -cne 'present') {
            $state = 'configuration_conflict'
        } elseif ($selected[0].state -cne 'Running') { $state = 'stopped' }
        elseif ($Facts.remote.status -ceq 'observed' -and -not $Facts.remote.online) { $state = 'offline' }
        elseif ($workers.Count -gt 0 -or ($Facts.remote.status -ceq 'observed' -and $Facts.remote.busy)) { $state = 'busy' }
        else { $state = 'running' }
        if ($selected.Count -ne 1) { $reasons.Add('SELECTED_SERVICE_MISSING_OR_DUPLICATE') }
        else {
            $serviceIdentityMatches = $selected[0].accountSid -ceq $Profile.expectedServiceSid
            $owner = @($processes | Where-Object { $_.processId -eq $selected[0].processId -and $_.name -ceq 'RunnerService.exe' })
            $child = @($listeners | Where-Object parentProcessId -EQ $selected[0].processId)
            $processIdentityMatches = $owner.Count -eq 1 -and $child.Count -eq 1 -and
                $owner[0].ownerSid -ceq $Profile.expectedServiceSid -and
                $child[0].ownerSid -ceq $Profile.expectedServiceSid
            $expectedServicePath = Join-Path $Profile.runnerRoot 'bin/RunnerService.exe'
            $expectedListenerPath = Join-Path $Profile.runnerRoot 'bin/Runner.Listener.exe'
            $localInstanceBound = $owner.Count -eq 1 -and $child.Count -eq 1 -and
                (Test-InspectionExecutablePath $selected[0].executablePath $expectedServicePath $Synthetic) -and
                (Test-InspectionExecutablePath $owner[0].executablePath $expectedServicePath $Synthetic) -and
                (Test-InspectionExecutablePath $child[0].executablePath $expectedListenerPath $Synthetic) -and
                $Facts.registration.status -ceq 'observed' -and $Facts.registration.scope -ceq 'repository' -and
                $Facts.registration.runnerId -eq $Profile.runnerId -and $Facts.registration.repository -ceq $Profile.repository
            if ($selected[0].state -cne 'Running' -or $selected[0].processId -eq 0) { $reasons.Add('SERVICE_NOT_RUNNING') }
        }
        $observerIsServiceIdentity = $identityKnown -and $identity.identitySid -ceq $Profile.expectedServiceSid
        if (-not $serviceIdentityMatches) { $reasons.Add('SERVICE_IDENTITY_NOT_CONFIRMED') }
        if (-not $processIdentityMatches) { $reasons.Add('PROCESS_IDENTITY_NOT_CONFIRMED') }
        if (-not $localInstanceBound) { $reasons.Add('LOCAL_REGISTRATION_AND_PATHS_NOT_BOUND') }
        if (-not $observerIsServiceIdentity -or $currentClass -cne 'non_administrator') {
            $reasons.Add('SERVICE_NON_ADMINISTRATOR_NOT_VERIFIED')
        }
        if ($Facts.runnerRoot.status -cne 'present') { $reasons.Add('RUNNER_ROOT_NOT_CONFIRMED') }
        if ($Facts.disk.status -cne 'observed' -or $Facts.disk.freeBytes -lt $Profile.minimumFreeBytes) {
            $reasons.Add('DISK_BUDGET_NOT_CONFIRMED')
        }
        $toolsMatch = $Facts.tools.Count -eq $Profile.requiredTools.Count
        foreach ($required in $Profile.requiredTools) {
            $found = @($Facts.tools | Where-Object name -CEQ $required.name)
            if ($found.Count -ne 1 -or $found[0].status -cne 'observed' -or
                $found[0].version -cne $required.expectedVersion) { $toolsMatch = $false }
        }
        if (-not $toolsMatch) { $reasons.Add('REQUIRED_TOOLS_NOT_CONFIRMED') }
        if ($Facts.remote.status -cne 'observed') { $reasons.Add('REMOTE_STATE_UNKNOWN') }
        elseif (-not $Facts.remote.registered -or $Facts.remote.runnerId -ne $Profile.runnerId -or
            $Facts.remote.repositoryId -ne $Profile.repositoryId -or $Facts.remote.repository -cne $Profile.repository -or
            -not $Facts.remote.private -or $Facts.remote.os -cne 'Windows') { $reasons.Add('REMOTE_PROFILE_MISMATCH') }
        elseif (-not $Facts.remote.online) { $reasons.Add('REMOTE_OFFLINE') }
    }
    $checksPass = $reasons.Count -eq 0
    $declaredTools = @()
    if ($null -ne $Profile) {
        $declaredTools = @($Profile.requiredTools | ForEach-Object {
            @{name = $_.name; expectedVersion = $_.expectedVersion}
        })
    }
    $reportedStatus = if ($Synthetic -and $checksPass) { 'SYNTHETIC_HEALTHY' }
        elseif ($checksPass) { 'HEALTHY' } else { 'NOT_READY' }
    $report = [ordered]@{
        schemaVersion = '1.0'; source = if ($Synthetic) { 'synthetic_fixture' } else { 'live_read_only' }
        observedAtUtc = [DateTimeOffset]::UtcNow.ToString('o'); status = $reportedStatus
        ready = [bool]($checksPass -and -not $Synthetic); exitCode = if ($checksPass) { 0 } else { 1 }
        declared = @{ profileConfigured = $null -ne $Profile; identity = 'redacted'; paths = 'redacted';
            toolRequirements = $declaredTools }
        observed = @{ platform = $Facts.platform; architecture = $Facts.architecture; instanceState = $state;
            serviceQuery = $Facts.serviceQuery.status; processQuery = $Facts.processQuery.status;
            serviceCount = $services.Count; activeServiceCount = $active.Count;
            listenerCount = $listeners.Count; workerCount = $workers.Count;
            currentIdentityClass = $currentClass; serviceIdentityMatches = $serviceIdentityMatches;
            processIdentityMatches = $processIdentityMatches; observerIsServiceIdentity = $observerIsServiceIdentity;
            localInstanceBound = $localInstanceBound; registration = $Facts.registration.status;
            runnerRoot = $Facts.runnerRoot.status; disk = $Facts.disk; tools = $Facts.tools; remote = @{
                status = $Facts.remote.status; registered = if ($Facts.remote.status -ceq 'observed') { $Facts.remote.registered } else { $null };
                online = if ($Facts.remote.status -ceq 'observed') { $Facts.remote.online } else { $null };
                busy = if ($Facts.remote.status -ceq 'observed') { $Facts.remote.busy } else { $null }
            } }
        missingOrUnhealthy = @($reasons); credentialIsolationVerified = $false;
        postRestartWorkloadVerified = $false; gatePass = $false; runtimeVerified = -not $Synthetic
        proofScope = 'read_only_preflight_only'
    }
    if ($PrivateDetails) {
        $report.privateDetails = @{ profile = $Profile; currentIdentitySid = $identity.identitySid;
            services = $services; processes = $processes }
    }
    return [pscustomobject]$report
}

function Invoke-RunnerInspection {
    param([string]$ProfilePath, [string]$FixturePath, [switch]$CheckRemote, [switch]$IncludePrivateDetails)
    $profile = Read-InspectionProfile $ProfilePath
    $synthetic = -not [string]::IsNullOrWhiteSpace($FixturePath)
    if ($synthetic) {
        if ($CheckRemote) { throw 'fixture_cannot_probe_network' }
        $fixture = Read-InspectionJson $FixturePath
        Assert-InspectionKeys $fixture @('schemaVersion', 'observations')
        if ($fixture.schemaVersion -cne '1.0') { throw 'invalid_version' }
        $facts = $fixture.observations
    } else { $facts = Get-InspectionObservations $profile ([bool]$CheckRemote) }
    return New-InspectionReport $profile $facts $synthetic ([bool]$IncludePrivateDetails)
}

function Write-RunnerInspection {
    param($Report, [ValidateSet('Json', 'Text')][string]$Format)
    if ($Format -eq 'Json') { $Report | ConvertTo-Json -Depth 12; return }
    Write-Output "Runner preflight: $($Report.status); source=$($Report.source); ready=$($Report.ready)"
    Write-Output "Instance: $($Report.observed.instanceState); active=$($Report.observed.activeServiceCount); workers=$($Report.observed.workerCount)"
    Write-Output "Identity: $($Report.observed.currentIdentityClass); root=$($Report.observed.runnerRoot); remote=$($Report.observed.remote.status)"
    Write-Output ('Missing/unhealthy: ' + ($Report.missingOrUnhealthy -join ', '))
    Write-Output 'Credential isolation, post-restart workload and Gate are not verified by this preflight.'
}

Export-ModuleMember -Function Invoke-RunnerInspection, Write-RunnerInspection
