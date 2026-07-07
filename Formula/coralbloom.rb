class Coralbloom < Formula
  desc "Infinite reaction-diffusion fluid animation rendered in the terminal"
  homepage "https://github.com/jverene/homebrew-coralbloom"
  url "https://github.com/jverene/homebrew-coralbloom/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "22027871771e138a3bbd623814962a334d0bcac41e6246e342204a24debbde8c"
  license "MIT"
  head "https://github.com/jverene/homebrew-coralbloom.git", branch: "main"

  depends_on "python@3.13"

  def install
    bin.install "core.py" => "coralbloom"
    # Pin shebang to brew's exact python; python@3.x is keg-only and not on PATH.
    # Use a literal string match (not a regex) so the first line is replaced
    # cleanly instead of being truncated mid-path.
    inreplace bin/"coralbloom", "#!/usr/bin/env python3", "#!#{Formula["python@3.13"].opt_bin}/python3.13"
  end

  test do
    assert_match "0.1.0", shell_output("#{bin}/coralbloom --version")
  end

  livecheck do
    url :stable
    strategy :github_latest
  end
end
