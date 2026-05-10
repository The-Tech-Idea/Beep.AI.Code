# Homebrew formula for Beep.AI.Code
# Tap: brew tap the-tech-idea/tap
# Install: brew install the-tech-idea/tap/beep

class Beep < Formula
  desc "Terminal-native AI coding assistant powered by Beep.AI.Server"
  homepage "https://github.com/The-Tech-Idea/Beep.AI.Code"
  version "0.1.0"
  license "MIT"

  on_macos do
    on_arm do
      url "https://github.com/The-Tech-Idea/Beep.AI.Code/releases/download/v#{version}/beep-darwin-aarch64"
      sha256 "PLACEHOLDER_SHA256_DARWIN_ARM64"
    end
    on_intel do
      url "https://github.com/The-Tech-Idea/Beep.AI.Code/releases/download/v#{version}/beep-darwin-x86_64"
      sha256 "PLACEHOLDER_SHA256_DARWIN_X86_64"
    end
  end

  on_linux do
    on_arm do
      url "https://github.com/The-Tech-Idea/Beep.AI.Code/releases/download/v#{version}/beep-linux-aarch64"
      sha256 "PLACEHOLDER_SHA256_LINUX_ARM64"
    end
    on_intel do
      url "https://github.com/The-Tech-Idea/Beep.AI.Code/releases/download/v#{version}/beep-linux-x86_64"
      sha256 "PLACEHOLDER_SHA256_LINUX_X86_64"
    end
  end

  def install
    if OS.mac?
      arch_suffix = Hardware::CPU.arm? ? "aarch64" : "x86_64"
      bin.install "beep-darwin-#{arch_suffix}" => "beep"
    else
      arch_suffix = Hardware::CPU.arm? ? "aarch64" : "x86_64"
      bin.install "beep-linux-#{arch_suffix}" => "beep"
    end
  end

  def caveats
    <<~EOS
      Run `beep setup` to configure your Beep.AI.Server connection.
      Documentation: https://github.com/The-Tech-Idea/Beep.AI.Code#readme
    EOS
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/beep --version")
  end
end
