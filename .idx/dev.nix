{ pkgs, ... }: {
  # Refreshed config to fix build error
  channel = "unstable";
  packages = [
    # pkgs.rustup # Temporarily disabled due to build failure
    # pkgs.gcc
    pkgs.nodejs_20
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.virtualenv
    pkgs.ffmpeg
    pkgs.curl
    pkgs.jq
    pkgs.openssh
  ];

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
