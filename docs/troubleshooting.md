# Tencent MCP - Troubleshooting

## Common Issues

### Bot Not Responding

| Symptom | Solution |
|---------|----------|
| No response to mention | `/invite @Tencent MCP` in channel |
| No response to /tencent | Check Slash Commands setup |
| "not_allowed_token_type" | Use Bot Token, not User Token |

**Diagnostics:**
```bash
# Check if bot is running
tail -f app.log

# Verify environment
cat .env | grep SLACK
```

### Connection Errors

#### Socket Mode Failed

```
slack_sdk.socket_mode...SocketModeError
```

**Solutions:**
1. Verify `SLACK_APP_TOKEN` starts with `xapp-`
2. Enable Socket Mode in Slack App settings
3. Check network/firewall

#### Tencent Cloud Auth Error

```
TencentCloudSDKException: [AuthFailure.SecretIdNotFound]
```

**Solutions:**
1. Verify `TENCENT_SECRET_ID` and `TENCENT_SECRET_KEY`
2. Check IAM/CAM permissions for MDL and MDC
3. Verify region is correct

### Performance Issues

#### Slow Dashboard Loading

**Current optimizations:**
- Parallel fetch (MDL + StreamLink simultaneous)
- 10-worker thread pool
- 50ms API jitter (reduced from 200ms)
- Cache prewarm on startup

**If still slow:**
```bash
# Check cache status in logs
grep "cache" app.log | tail -10

# Restart to reset cache
./scripts/restart.sh
```

#### Rate Limit Errors

```
RequestLimitExceeded
```

**Solutions:**
1. Reduce refresh frequency
2. Wait for cache TTL (120s)
3. Increase jitter in `_fetch_single_flow_detail()`

### UI/UX Issues

#### Modal Not Updating

**Causes:**
- `expired_trigger_id` (took > 3s to respond)
- Network timeout

**Solutions:**
- Already mitigated by async modal pattern
- Check Slack API status

#### Status Shows "UNKNOWN"

**Causes:**
- API returned unexpected status format
- SDK client connection issue

**Solutions:**
1. Check `_normalize_streamlink_status()` logic
2. Verify thread-safe client initialization
3. Check API response in debug logs

---

## Logs

```bash
# Real-time logs
tail -f app.log

# Search for errors
grep -i "error\|exception" app.log

# Filter by component
grep "TencentCloudClient" app.log
grep "SlackUI" app.log
```

---

## Reset & Recovery

### Full Reset

```bash
# Stop everything
./scripts/shutdown.sh

# Clear cache (delete pycache)
find . -type d -name "__pycache__" -exec rm -rf {} +

# Restart
./scripts/start.sh
```

### Token Refresh

1. Go to Slack App settings
2. OAuth & Permissions → Reinstall to Workspace
3. Copy new `xoxb-` token
4. Update `.env`
5. Restart bot

---

## Migration Notes

### From v1 (app.py) to v2 (app_v2.py)

| v1 | v2 |
|----|-----|
| `tencent_client.py` | `tencent_cloud_client.py` |
| Mock data | Real Tencent Cloud SDK |
| Message-based UI | Modal-based dashboard |
| Manual refresh | Auto-refresh on action |

### Environment Variable Changes

| Old | New | Notes |
|-----|-----|-------|
| `TENCENT_API_URL` | Removed | SDK handles endpoints |
| `TENCENT_API_KEY` | `TENCENT_SECRET_ID` | Renamed |
| `TENCENT_API_SECRET` | `TENCENT_SECRET_KEY` | Renamed |
| - | `TENCENT_REGION` | New requirement |

---

## Support

1. Check this troubleshooting guide
2. Review `app.log` for detailed errors
3. Check `docs/architecture.md` for system understanding
4. Open GitHub issue with logs
