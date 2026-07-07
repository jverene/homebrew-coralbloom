class Coralbloom < Formula
  desc "Infinite reaction-diffusion fluid animation rendered in the terminal"
  homepage "https://github.com/jverene/coralbloom"
  url "https://github.com/jverene/coralbloom/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "daee3d23f2092a68ac09793ac3ece72e3733727f35c25168cb81af46405cdd0e"
  version "0.1.0"
  license "MIT"
  head "https://github.com/jverene/coralbloom.git", branch: "main"

  depends_on "python@3.13"

  def install
    bin.install "core.py" => "coralbloom"
    # Pin shebang to brew's exact python; python@3.x is keg-only and not on PATH.
    inreplace bin/"coralbloom", %r{^#!.*$}, "#!#{Formula["python@3.13"].opt_bin}/python3"
  end

  test do
    assert_match "0.1.0", shell_output("#{bin}/coralbloom --version")
  end

  livecheck do
    url :stable
    strategy :github_latest
  end
end
