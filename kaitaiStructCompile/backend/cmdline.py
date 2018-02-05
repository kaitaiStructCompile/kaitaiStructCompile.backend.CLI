import typing
import sys, os, io, subprocess
import tempfile
from functools import wraps
from pathlib import Path


class Flag:
	slots = ("value",)

	def __init__(self, value):
		self.value = value

	def __hash__(self):
		return hash(self.value)

	def __bool__(self):
		return self.value

	def __repr__(self):
		return self.__class__.__name__ + "(" + repr(self.value) + ")"

langNamespaceCliArgMapping = {
	"python": "python-package",
	"go": "go-package",
	"jre": "java-package",
	"dotNet": "dotnet-namespace",
	"php": "php-namespace",
	"cpp": "cpp-namespace",
	"nim": "nim-module"
}

class paramsRemapping:
	def verbose(v):
		if v:
			return {"--verbose": ",".join(v)}
		else:
			return {}

	def opaqueTypes(v):
		return {"--opaque-types": str(v).lower()}

	def autoRead(v):
		return {"--no-auto-read": Flag(not v)}

	def readStoresPos(v):
		return {"--read-pos": Flag(v)}

	##########

	def namespaces(v):
		res = {}
		for langName, v in v.items():
			if v is not None:
				res["--" + langNamespaceCliArgMapping[langName]] = v
		return res

	def target(v):
		return {"--target": v}

	def destDir(v):
		return {"--outdir": str(v)}

	def additionalFlags(v):
		if isinstance(v, (list, tuple)):
			f = Flag(True)
			return {kk: f for kk in v}
		else:
			res = {}
			for vk, vv in v.items():
				if vv is None:
					vv = Flag(True)
				res[vk] = vv
			return res

	def importPath(v):
		return {"--import-path": str(v)}


def init(ICompilerModule, KaitaiCompilerException, utils, defaults):

	osBinariesNamesTable = {
		"nt": (defaults.compilerName + ".bat"),
		"posix": defaults.compilerName
	}

	class CLIPrefsStorage(ICompilerModule.IPrefsStorage):
		@wraps(ICompilerModule.IPrefsStorage.__init__)
		def __init__(self, **kwargs):
			self._stor = {}
			for argName, v in kwargs.items():
				if v is not None:
					if hasattr(paramsRemapping, argName):
						f = getattr(paramsRemapping, argName)
						self._stor.update(f(v))
					else:
						raise ValueError("`" + argName + "` is not an implemented arg")

		def __iadd__(self, other):
			self._stor.update(other._stor)
			return self

		def __add__(self, other):
			res = self.__class__()
			res += self
			res += other
			return res

		def __repr__(self):
			#return self.__class__.__name__+"<"+repr(self._stor)+">"
			return self.__class__.__name__ + "<" + " ".join(self()) + ">"

		def __call__(self):
			params = []
			for k, v in self._stor.items():
				if v is not None:
					if not isinstance(v, Flag):
						params.append(k)
						params.append(v)
					else:
						if v:
							params.append(k)

			return params

	class CLICompiler(ICompilerModule.ICompiler):
		def __init__(self, progressCallback=None, dirs=None, namespaces=None, additionalFlags: typing.Iterable[str] = (), importPath=None, verbose=(), opaqueTypes=None, autoRead: bool = None, readStoresPos: bool = None, target: str = "python", **kwargs):
			super().__init__(progressCallback, dirs)

			self.compilerExecutable = self.dirs.bin / osBinariesNamesTable[os.name]

			self.commonFlags = CLIPrefsStorage(additionalFlags=("--ksc-json-output",))  # flags needed for this class to work correctly, though a user is allowed to redefine

			self.commonFlags += CLIPrefsStorage(namespaces=namespaces, additionalFlags=additionalFlags, importPath=importPath, verbose=verbose, opaqueTypes=opaqueTypes, autoRead=autoRead, readStoresPos=readStoresPos, **kwargs)

			if not self.compilerExecutable.exists():
				raise KaitaiCompilerException("Compiler executable " + str(self.compilerExecutable) + " doesn't exist")

		def compile_(self, sourceFilesAbsPaths: typing.Iterable[Path], destDir: Path, additionalFlags: typing.Iterable[str], verbose, opaqueTypes, autoRead: bool, readStoresPos: bool, target: str = "python", needInMemory: bool = False, **kwargs) -> typing.Mapping[str, ICompilerModule.ICompileResult]:
			if destDir is None:
				with tempfile.TemporaryDirectory() as tmpDir:
					return self.compile__(sourceFilesAbsPaths, Path(tmpDir), additionalFlags, verbose, opaqueTypes, autoRead, readStoresPos, target, needInMemory, **kwargs)
			else:
				return self.compile__(sourceFilesAbsPaths, destDir, additionalFlags, verbose, opaqueTypes, autoRead, readStoresPos, target, needInMemory, **kwargs)

		def compile__(self, sourceFilesAbsPaths: typing.Iterable[Path], destDir: Path, additionalFlags: typing.Iterable[str], verbose, opaqueTypes, autoRead: bool, readStoresPos: bool, target: str = "python", needInMemory: bool = False, **kwargs) -> typing.Mapping[str, ICompilerModule.ICompileResult]:
			"""Compiles KS package with kaitai-struct-compiler"""
			print("commonFlags", self.commonFlags)
			params = [str(self.compilerExecutable)]

			params += (self.commonFlags + CLIPrefsStorage(destDir=destDir, additionalFlags=additionalFlags, verbose=verbose, opaqueTypes=opaqueTypes, autoRead=autoRead, readStoresPos=readStoresPos, target=target))()

			params.extend((str(p) for p in sourceFilesAbsPaths))

			with subprocess.Popen(params, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as proc:
				with io.TextIOWrapper(proc.stdout) as stdoutPipe:
					msg = stdoutPipe.read()
				proc.wait()
				# print(msg, proc.returncode)

				if proc.returncode or msg.find("Exception in thread") > -1:
					raise KaitaiCompilerException(msg)

			res = utils.json.loads(msg)
			from pprint import pprint

			pprint(res)

			if needInMemory:

				def genResult(moduleName: str, resultPath: Path, topLevelName: str, msg=None):
					return ICompilerModule.InMemoryCompileResult(moduleName, topLevelName, msg, resultPath.read_text(encoding="utf-8"))

			else:

				def genResult(moduleName: str, resultPath: Path, topLevelName: str, msg=None):
					return ICompilerModule.InFileCompileResult(moduleName, topLevelName, msg, resultPath)

			resultModules = {}
			errors = []

			for srcFile, fRes in res.items():
				srcFile = Path(srcFile)
				if "output" in fRes:
					for packageName, specResult in fRes["output"][target].items():
						for fSpecResultDescr in specResult["files"]:
							resultModules[packageName] = genResult(packageName, destDir / fSpecResultDescr["fileName"], specResult["topLevelName"], msg)
				if "errors" in fRes:
					for error in fRes["errors"]:
						if error["file"] == "(main)":
							error["file"] = srcFile
						errors.append(error)
				if "firstSpecName" in fRes:
					resultModules[fRes["firstSpecName"]].sourcePath = srcFile

			print(resultModules)
			if errors:
				raise KaitaiCompilerException(errors)
			return resultModules

	return CLICompiler
