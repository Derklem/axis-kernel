import os
import shutil
import stat

def install_pre_commit():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(base_dir)
    git_hooks_dir = os.path.join(repo_root, ".git", "hooks")

    source_hook = os.path.join(base_dir, "hooks", "pre-commit")
    target_hook = os.path.join(git_hooks_dir, "pre-commit")

    if not os.path.exists(git_hooks_dir):
        print("Error: .git/hooks directory not found.")
        return

    shutil.copy2(source_hook, target_hook)

    # Make executable
    st = os.stat(target_hook)
    os.chmod(target_hook, st.st_mode | stat.S_IEXEC)

    print("Installed Axis Advisory pre-commit hook.")

if __name__ == "__main__":
    install_pre_commit()
