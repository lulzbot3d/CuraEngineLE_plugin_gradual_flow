import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, update_conandata
from conan.tools.microsoft import check_min_vs, is_msvc_static_runtime, is_msvc
from conan.tools.scm import Version

from jinja2 import Template

required_conan_version = ">=1.58.0 <2.0.0"


class CuraEngineLEGradualFlowPluginConan(ConanFile):
    name = "curaenginele_plugin_gradual_flow"
    description = "CuraEngineLE plugin for gradually smoothing the flow to limit high-flow jumps"
    author = "UltiMaker, FAME3D LLC."
    license = "AGPL-3.0"
    url = "https://github.com/lulzbot3d/CuraEngineLE_plugin_gradual_flow"
    homepage = "https://ultimaker.com"
    topics = ("protobuf", "asio", "plugin", "curaenginele", "gcode-generation", "3D-printing")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def set_version(self):
        if not self.version:
            self.version = self.conan_data["version"]

    @property
    def _min_cppstd(self):
        return 20

    @property
    def _compilers_minimum_version(self):
        return {
            "gcc": "11",
            "clang": "14",
            "apple-clang": "13",
            "msvc": "192",
            "visual_studio": "17",
        }

    @property
    def _cura_plugin_name(self):
        return "CuraEngineLEGradualFlow"

    @property
    def _api_version(self):
        return "8"

    @property
    def _sdk_versions(self):
        return ["8.4.0"]

    @property
    def _max_sdk_version(self):
        sorted_versions = sorted(self._sdk_versions, key=lambda v: Version(v))
        return sorted_versions[-1]

    def _generate_cmdline(self):
        with open(os.path.join(self.source_folder, "templates", "include", "plugin", "cmdline.h.jinja"), "r") as f:
            template = Template(f.read())

        version = Version(self.version)
        with open(os.path.join(self.source_folder, "include", "plugin", "cmdline.h"), "w") as f:
            f.write(template.render(cura_plugin_name=self._cura_plugin_name.lower(),
                                    description=self.description,
                                    version=f"{version.major}.{version.minor}.{version.patch}",
                                    curaengine_plugin_name=self.name))

    def _generate_cura_plugin_constants(self):
        with open(os.path.join(self.source_folder, "templates", "cura_plugin", "constants.py.jinja"), "r") as f:
            template = Template(f.read())

        version = Version(self.version)
        with open(os.path.join(self.source_folder, self._cura_plugin_name, "constants.py"), "w") as f:
            f.write(template.render(cura_plugin_name=self._cura_plugin_name,
                                    version=f"{version.major}.{version.minor}.{version.patch}",
                                    curaengine_plugin_name=self.name,
                                    settings_prefix=f"_plugin__{self._cura_plugin_name.lower()}__{version.major}_{version.minor}_{version.patch}_"))

    def _generate_plugin_metadata(self):
        with open(os.path.join(self.source_folder, "templates", "cura_plugin", "plugin.json.jinja"), "r") as f:
            template = Template(f.read())

        version = Version(self.version)
        with open(os.path.join(self.source_folder, self._cura_plugin_name, "plugin.json"), "w") as f:
            f.write(template.render(cura_plugin_name=self._cura_plugin_name,
                                    author=self.author,
                                    version=f"{version.major}.{version.minor}.{version.patch}",
                                    description=self.description,
                                    api_version=self._api_version,
                                    sdk_versions=self._sdk_versions))

    def _generate_package_metadata(self):
        with open(os.path.join(self.source_folder, "templates", "cura_plugin", "package.json.jinja"), "r") as f:
            template = Template(f.read())

        version = Version(self.version)
        with open(os.path.join(self.source_folder, self._cura_plugin_name, "package.json"), "w") as f:
            f.write(template.render(author_id=self.author.lower(),
                                    author=self.author,
                                    website_author=self.homepage,
                                    description=self.description,
                                    display_name=self._cura_plugin_name,
                                    package_id=self._cura_plugin_name,
                                    version=f"{version.major}.{version.minor}.{version.patch}",
                                    sdk_version_major=Version(self._max_sdk_version).major,
                                    sdk_version=self._max_sdk_version,
                                    website=self.url
                                    ))

    def _generate_bundled_metadata(self):
        with open(os.path.join(self.source_folder, "templates", "cura_plugin", "bundled.json.jinja"), "r") as f:
            template = Template(f.read())

        version = Version(self.version)
        with open(os.path.join(self.source_folder, self._cura_plugin_name, f"bundled_{self._cura_plugin_name}.json"), "w") as f:
            f.write(template.render(package_id=self._cura_plugin_name,
                                    display_name=self._cura_plugin_name,
                                    description=self.description,
                                    version=f"{version.major}.{version.minor}.{version.patch}",
                                    sdk_version=self._max_sdk_version,
                                    author=self.author,
                                    website=self.url,
                                    website_author=self.homepage))

    def export(self):
        update_conandata(self, {"version": self.version})

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)
        copy(self, "*.jinja", os.path.join(self.recipe_folder, "templates"), os.path.join(self.export_sources_folder, "templates"))
        copy(self, "*", os.path.join(self.recipe_folder, "src"), os.path.join(self.export_sources_folder, "src"))
        copy(self, "*", os.path.join(self.recipe_folder, "include"), os.path.join(self.export_sources_folder, "include"))
        copy(self, "*", os.path.join(self.recipe_folder, "tests"), os.path.join(self.export_sources_folder, "tests"))
        copy(self, "*", os.path.join(self.recipe_folder, self._cura_plugin_name), os.path.join(self.export_sources_folder, self._cura_plugin_name))

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        self.options["boost"].header_only = True

        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)
        self.cpp.package.resdirs = [os.path.join("res", "plugins", self._cura_plugin_name).replace("\\", "/"),
                                    os.path.join("res", "bundled_packages").replace("\\", "/")]

    def requirements(self):
        for req in self.conan_data["requirements"]:
            self.requires(req)
        self.requires("protobuf/3.21.9")
        self.requires("boost/1.82.0")
        self.requires("asio-grpc/2.6.0")
        self.requires("openssl/1.1.1w")
        self.requires("spdlog/1.12.0")
        self.requires("fmt/10.1.1")
        self.requires("docopt.cpp/0.6.3")
        self.requires("range-v3/0.12.0")
        self.requires("clipper/6.4.2")
        self.requires("ctre/3.7.2")
        self.requires("neargye-semver/0.3.0")

    def build_requirements(self):
        self.test_requires("standardprojectsettings/[>=0.1.0]@lulzbot/stable")
        if not self.conf.get("tools.build:skip_test", False, check_type=bool):
            self.test_requires("catch2/3.4.0")

    def validate(self):
        # validate the minimum cpp standard supported. For C++ projects only
        if self.settings.compiler.cppstd:
            check_min_cppstd(self, self._min_cppstd)
        check_min_vs(self, 191)
        if not is_msvc(self):
            minimum_version = self._compilers_minimum_version.get(str(self.settings.compiler), False)
            if minimum_version and Version(self.settings.compiler.version) < minimum_version:
                raise ConanInvalidConfiguration(
                    f"{self.ref} requires C++{self._min_cppstd}, which your compiler does not support."
                )
        if is_msvc(self) and self.options.shared:
            raise ConanInvalidConfiguration(f"{self.ref} can not be built as shared on Visual Studio and msvc.")

    def generate(self):
        self._generate_cmdline()
        self._generate_cura_plugin_constants()
        self._generate_plugin_metadata()
        self._generate_package_metadata()
        self._generate_bundled_metadata()

        # BUILD_SHARED_LIBS and POSITION_INDEPENDENT_CODE are automatically parsed when self.options.shared or self.options.fPIC exist
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_TESTS"] = not self.conf.get("tools.build:skip_test", False, check_type=bool)
        if is_msvc(self):
            tc.variables["USE_MSVC_RUNTIME_LIBRARY_DLL"] = not is_msvc_static_runtime(self)
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        tc.generate()

        tc = CMakeDeps(self)
        tc.generate()

        tc = VirtualBuildEnv(self)
        tc.generate(scope="build")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        ext = ".exe" if self.settings.os == "Windows" else ""
        copy(self, pattern=f"curaenginele_plugin_gradual_flow{ext}", dst=os.path.join(self.package_folder, "bin"), src=os.path.join(self.build_folder))

        copy(self, pattern=f"bundled_{self._cura_plugin_name}.json", dst=os.path.join(self.package_folder, "res", "bundled_packages"), src=os.path.join(self.source_folder, self._cura_plugin_name))
        copy(self, pattern="*", dst=os.path.join(self.package_folder, "res", "plugins", self._cura_plugin_name), src=os.path.join(self.source_folder, self._cura_plugin_name))

    def deploy(self):
        ext = ".exe" if self.settings.os == "Windows" else ""
        copy(self, pattern=f"curaenginele_plugin_gradual_flow{ext}", dst=self.install_folder, src=os.path.join(self.package_folder, "bin"))
        copy(self, pattern="*", dst=os.path.join(self.install_folder, self._cura_plugin_name), src=os.path.join(self.package_folder, "res"))
