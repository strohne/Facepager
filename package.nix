# This file defines the Facepager package
# Building PySide6 from PyPI instead of using nixpkgs version

{ lib
, python311
, python311Packages
, qt6
, bash
, fetchPypi
, makeWrapper
, cmake
, ninja
}:

python311Packages.buildPythonApplication {
  pname = "facepager";
  version = "4.6.0";

  src = ./.;

  # Use pyproject format to handle requirements.txt
  format = "other";

  # Build-time dependencies
  nativeBuildInputs = [
    qt6.wrapQtAppsHook
    makeWrapper
    python311Packages.pip
    cmake
    ninja
  ];

  # Qt runtime libraries
  buildInputs = [
    qt6.qtbase
    qt6.qtsvg
    qt6.qtwebengine
  ];

  # Python dependencies - we'll install via pip during build
  propagatedBuildInputs = with python311Packages; [
    pip
    setuptools
    wheel
  ];

  buildPhase = ''
    runHook preBuild

    # Create a temporary venv to install dependencies
    ${python311}/bin/python -m venv venv
    source venv/bin/activate

    # Install dependencies from requirements.txt via pip
    # This will build PySide6 with WebEngine support
    pip install --no-cache-dir -r requirements.txt

    runHook postBuild
  '';

  installPhase = ''
    runHook preInstall

    mkdir -p $out/bin
    mkdir -p $out/share/facepager
    mkdir -p $out/lib/python${python311.pythonVersion}/site-packages

    # Copy application files
    cp -r src/* $out/share/facepager/
    cp -r icons $out/share/facepager/
    cp -r presets $out/share/facepager/
    cp -r docs $out/share/facepager/

    # Copy the installed Python packages from venv
    cp -r venv/lib/python${python311.pythonVersion}/site-packages/* \
      $out/lib/python${python311.pythonVersion}/site-packages/

    # Create wrapper with proper PYTHONPATH
    makeWrapper ${python311}/bin/python $out/bin/facepager \
      --prefix PYTHONPATH : "$out/lib/python${python311.pythonVersion}/site-packages" \
      --add-flags "$out/share/facepager/Facepager.py" \
      --chdir "$out/share/facepager"

    runHook postInstall
  '';

  meta = with lib; {
    description = "An application for automated data retrieval from APIs and web scraping";
    longDescription = ''
      Facepager was made for fetching public available data from YouTube,
      Twitter and other websites on the basis of APIs and webscraping.
      All data is stored in a SQLite database and may be exported to csv.

      This package builds PySide6 with WebEngine support from PyPI.
    '';
    homepage = "https://github.com/strohne/Facepager";
    license = licenses.mit;
    maintainers = [ ];
    platforms = platforms.unix;
    mainProgram = "facepager";
  };
}
