
{ pkgs, ... }: {
  channel = "stable-24.05"; # Or "unstable"

  packages = [
    pkgs.python3
    # Add other necessary packages here
    pkgs.python3Packages.flask
    pkgs.python3Packages.google-generativeai
  ];

  idx = {
    extensions = [
      "ms-python.python"
      # Add other extensions here
    ];

    workspace = {
      onCreate = {
        install = "python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt";
        # Add other onCreate tasks here
      };
      # onStart = { ... }; # Optional: tasks to run on workspace start
    };

    previews = {
      enable = true;
      previews = {
        web = {
          command = [ "./devserver.sh" ];
          env = { PORT = "$PORT"; };
          manager = "web";
        };
      };
    };
  };
}
