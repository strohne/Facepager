{ pkgs, lib, config, inputs, ... }:

{
  # https://devenv.sh/basics/
  env.GREET = "devenv";

  # https://devenv.sh/packages/
  packages = with pkgs; [
    git
    upx
  ];

  # https://devenv.sh/languages/
  languages.python = {
    enable = true;
    package = pkgs.python310;

    # Create a virtual environment and install requirements.txt
    venv.enable = true;
    venv.requirements = ./requirements.txt;
  };

  # https://devenv.sh/scripts/
  enterShell = ''
    echo ""
    echo "🐍 Python ${config.languages.python.package.version} environment activated"
    echo "📦 Virtual environment: .devenv/state/venv"
    echo "✅ Requirements from requirements.txt installed"
    echo ""
  '';
}
