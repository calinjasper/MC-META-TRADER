# PocketBase Network Setup Guide

## Overview

PocketBase has been configured to connect to `http://192.168.173.112:8090` instead of localhost.

## Configuration Complete

All application files and scripts have been updated to use the new network IP address:
- ✅ Main application (`src/main.py`)
- ✅ All setup scripts (`scripts/setup/`)
- ✅ All database scripts (`scripts/database/`)
- ✅ All export scripts (`scripts/export/`)
- ✅ All diagnostic tools (`tools/`)
- ✅ All test scripts (`tests/`)

## Server Setup Required

To host PocketBase on the network IP (192.168.173.112), you need to:

### 1. Start PocketBase with Network Binding

On the server machine (192.168.173.112), start PocketBase with:

```bash
# Windows
pocketbase.exe serve --http=0.0.0.0:8090

# Linux/Mac
./pocketbase serve --http=0.0.0.0:8090
```

**Important**: The `--http=0.0.0.0:8090` flag makes PocketBase listen on all network interfaces, not just localhost.

### 2. Configure Firewall

Ensure port 8090 is open on the server:

**Windows Firewall:**
```powershell
# Allow inbound connections on port 8090
New-NetFirewallRule -DisplayName "PocketBase" -Direction Inbound -LocalPort 8090 -Protocol TCP -Action Allow
```

**Linux (iptables):**
```bash
sudo iptables -A INPUT -p tcp --dport 8090 -j ACCEPT
```

**Linux (ufw):**
```bash
sudo ufw allow 8090/tcp
```

### 3. Verify Network Connectivity

Test connection from your machine:

```bash
# Test health endpoint
python tools/test_pocketbase_connection.py

# Or manually
curl http://192.168.173.112:8090/api/health
```

### 4. Access Admin UI

Once PocketBase is running on the network IP, access the admin UI at:
```
http://192.168.173.112:8090/_/
```

## Security Considerations

⚠️ **Important Security Notes:**

1. **Authentication**: Ensure PocketBase admin account has a strong password
2. **Network Access**: Consider restricting access to specific IPs if possible
3. **HTTPS**: For production, consider setting up HTTPS/TLS
4. **Firewall**: Only allow port 8090 from trusted networks

## Troubleshooting

### Connection Failed

If connection test fails:

1. **Check PocketBase is running:**
   ```bash
   # On server
   netstat -an | findstr 8090  # Windows
   netstat -an | grep 8090     # Linux
   ```

2. **Check firewall rules:**
   - Verify port 8090 is open
   - Check if Windows Firewall or iptables is blocking

3. **Verify IP address:**
   ```bash
   # On server, check network IP
   ipconfig  # Windows
   ifconfig  # Linux
   ```

4. **Test from server itself:**
   ```bash
   # Should work from server
   curl http://192.168.173.112:8090/api/health
   ```

### Connection Works but Authentication Fails

- Verify admin credentials are correct
- Check if PocketBase requires authentication for API access
- Ensure you're using the correct admin email/password

## Updated Files Summary

All references to `http://127.0.0.1:8090` have been changed to `http://192.168.173.112:8090` in:

- **Core Application**: 1 file
- **Setup Scripts**: 4 files
- **Database Scripts**: 5 files
- **Export Scripts**: 2 files
- **Tools**: 9 files
- **Tests**: 1 file

**Total: 22 files updated**

## Next Steps

1. Start PocketBase on the server with network binding
2. Configure firewall rules
3. Test connection using `tools/test_pocketbase_connection.py`
4. Start the trading system - it will automatically connect to the network PocketBase

