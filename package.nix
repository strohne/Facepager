# This file defines the Facepager package
# It's called by flake.nix to build the package for different systems

{lib, python310Packages, python310, qt6, bash, ...}:

python310Packages.buildPythonApplication {
  pname = "facepager";
  version = "4.6.0-flake_test";

  src = ./.;

  # Python dependencies from requirements.txt
  propagatedBuildInputs = with python310Packages; [
    sqlalchemy
    python-dateutil
    requests
    requests-oauthlib
    requests-toolbelt
    rauth
    lxml
    cchardet
    pyjsparser
    tldextract
    cssselect
    markdown
    pyside6
    rdflib
    pillow
  ];

  # Ensures Qt applications are properly wrapped
  nativeBuildInputs = [
    qt6.wrapQtAppsHook
  ];

  # Qt runtime libraries
  buildInputs = [
    qt6.qtbase
    qt6.qtsvg
    qt6.qtwebengine
  ];

  # Custom installation since there's no setup.py
  format = "other";

  installPhase = ''
    runHook preInstall

    mkdir -p $out/bin
    mkdir -p $out/share/facepager

    # Copy all necessary files
    cp -r src/* $out/share/facepager/
    cp -r icons $out/share/facepager/
    cp -r presets $out/share/facepager/
    cp -r docs $out/share/facepager/

    # Create executable wrapper
    cat > $out/bin/facepager << EOF
    #!${bash}/bin/bash
    cd $out/share/facepager
    exec ${python310}/bin/python Facepager.py "\$@"
    EOF

    chmod +x $out/bin/facepager

    runHook postInstall
  '';

  meta = with lib; {
    description = "An application for automated data retrieval from APIs and web scraping";
    longDescription = ''
      Facepager was made for fetching public available data from YouTube,
      Twitter and other websites on the basis of APIs and webscraping.
      All data is stored in a SQLite database and may be exported to csv.
    '';
    homepage = "https://github.com/strohne/Facepager";
    license = licenses.mit;
    maintainers = [ ];
    platforms = platforms.unix;
    mainProgram = "facepager";
  };
}
