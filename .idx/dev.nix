{ pkgs, ... }: {
  # Refreshed config to fix build error
  channel = "unstable";
  packages = [
    # pkgs.rustup # Temporarily disabled due to build failure
    # pkgs.gcc
    pkgs.python3
    pkgs.python311Packages.pip
    pkgs.python311Packages.virtualenv
    pkgs.python311Packages.requests
    pkgs.python311Packages.python-dotenv
    pkgs.ffmpeg
    pkgs.stdenv.cc.cc.lib
    pkgs.libGL
    pkgs.xorg.libX11
    pkgs.openssh
  ];

  env = {
    LD_LIBRARY_PATH = "${pkgs.stdenv.cc.cc.lib}/lib:${pkgs.libGL}/lib:${pkgs.xorg.libX11}/lib";
  };

  idx = {
    extensions = [
      "rust-lang.rust-analyzer"
      "google.gemini-cli-vscode-ide-companion"
      "ms-python.debugpy"
      "ms-python.python"
      "WakaTime.vscode-wakatime"
      "roipoussiere.cadquery"
      "slevesque.vscode-3dviewer"
    ];
    previews = {
      enable = true;
      previews = {};
    };
  };
}