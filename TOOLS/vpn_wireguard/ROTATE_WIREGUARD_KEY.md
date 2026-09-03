# Rotate compromised SSH key (id_rsa.ppk)

Purpose
-------
Steps to generate a new SSH keypair, install the new public key on the server (UpCloud), validate access, remove the compromised key, convert to PuTTY .ppk if needed, and securely delete old copies. Designed so another agent or operator can run the commands.

Prerequisites
-------------
- Local machine with OpenSSH (ssh, ssh-keygen, scp) or PuTTY tools (puttygen) on Windows
- Root or sudo-capable account on the remote server (or access to the server console via UpCloud)
- New key will be ed25519 (recommended) or RSA (if compatibility required)

Important safety notes
----------------------
1. Do not delete the old key until the new key is tested successfully from a separate terminal session.
2. Backup the server's current authorized_keys before changes.
3. Treat the compromised key as revoked: rotate any other services using it and assume compromise.

High-level plan
----------------
1. Generate new keypair locally.
2. Convert to PPK (Windows/PuTTY) if needed.
3. Upload the public key to the server (append to ~/.ssh/authorized_keys).
4. Test new key in a new session.
5. Remove the old key from authorized_keys and delete local copies of the compromised key.
6. Rotate any other credentials that may have used the same key.

Detailed commands (agent-run)
-----------------------------
Replace USER and HOST with your remote username and server IP/hostname.

A. Generate a new keypair (ed25519 recommended)

# Linux/macOS / WSL / Git Bash
ssh-keygen -t ed25519 -C "michi05@$(hostname -f)" -f ~/.ssh/wg_rotate_ed25519
# Follow prompts; use a secure passphrase (recommended)

# If ed25519 is not supported or you need RSA (compatibility):
ssh-keygen -t rsa -b 4096 -C "michi05@$(hostname -f)" -f ~/.ssh/wg_rotate_rsa

B. Secure the private key locally
chmod 600 ~/.ssh/wg_rotate_ed25519
# (for rsa file, adjust filename accordingly)

C. Convert to PuTTY PPK (Windows) — optional
# On Windows with puttygen in PATH
puttygen C:\Users\<user>\\.ssh\\wg_rotate_ed25519 -o C:\Users\<user>\\.ssh\\wg_rotate_ed25519.ppk
# Or using full path to puttygen.exe

D. Copy the public key to the server (safe append)
# Preferred: ssh-copy-id (if available)
ssh-copy-id -i ~/.ssh/wg_rotate_ed25519.pub USER@HOST

# If ssh-copy-id is not available, do the manual safe-append method
ssh USER@HOST 'mkdir -p ~/.ssh && chmod 700 ~/.ssh'
scp ~/.ssh/wg_rotate_ed25519.pub USER@HOST:~/wg_rotate_ed25519.pub
ssh USER@HOST 'cat ~/wg_rotate_ed25519.pub >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && rm ~/wg_rotate_ed25519.pub'

E. Backup current authorized_keys before removing anything
ssh USER@HOST 'cp ~/.ssh/authorized_keys ~/.ssh/authorized_keys.bak_$(date +%Y%m%d_%H%M%S)'

F. Test login with the new key from a new terminal session (do NOT close current sessions)
ssh -i ~/.ssh/wg_rotate_ed25519 USER@HOST
# On Windows with PuTTY, load the .ppk into Pageant or use it in PuTTY session config.

G. Once login works, remove the old compromised key from authorized_keys
# Identify old key entry by fingerprint or filename comment if present. Example remove by edit:
ssh USER@HOST "awk '!/id_rsa.ppk/ {print}' ~/.ssh/authorized_keys > ~/.ssh/authorized_keys.tmp && mv ~/.ssh/authorized_keys.tmp ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"

# If the old entry does not contain the filename, compare fingerprints locally:
ssh-keygen -lf ~/.ssh/wg_rotate_ed25519.pub  # fingerprint of new key
# On server list fingerprints: for k in ~/.ssh/authorized_keys; do ssh-keygen -lf <(echo "$k"); done  (or inspect manually), then remove matching line

H. Revoke/remove old private key files locally and backups
# Securely remove local copies (if on Linux with shred available):
shred -u /path/to/old/id_rsa.ppk
# Or on Windows, securely delete with your secure-delete tool or simply remove but ensure backups are purged.

I. Rotate related credentials and update automation
- Check crontabs, systemd units, docker-compose mounts, or scripts that reference the old private key path and update to the new key path.
- Update any CI/CD secrets or vault entries that may have stored the key.

J. Update UpCloud control panel (if the key is also listed in their UI)
- Log in to UpCloud portal and replace the SSH key for the server if it was injected via the control panel.

K. Audit and notify
- Assume compromise: rotate any other keys or passwords that might have co-existed with this private key.
- Inform team members to re-clone repo if they had local copies and to remove the compromised key.
- If the key allowed access to other services (e.g., GitHub deploy keys), rotate those credentials as well.

Optional: If the server had the private key (e.g., for wireguard peer config), review WireGuard container config and peer files. Rotating SSH key does not change WireGuard keys.

Post-rotation validation checklist
---------------------------------
- [ ] New SSH login works from at least one separate terminal.
- [ ] Old key entries removed from authorized_keys
- [ ] Old private key files securely deleted from all machines/backups
- [ ] Any automation using the old key is updated and tested
- [ ] Team notified and other dependent keys rotated where required

Contact
-------
If help is needed to run commands or to convert keys on Windows (PuTTY), list the local OS and available tools and an operator/agent will run the conversion and installation steps.
