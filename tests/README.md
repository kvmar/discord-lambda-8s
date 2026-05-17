# Pre-Queue Feature Tests

Comprehensive test suite for the pre-queue (waiting room) feature.

## Test Files

### `conftest.py`
Shared pytest fixtures and mocks for all tests:
- `mock_interaction`: Mock Discord interaction
- `queue_record_waiting`: Queue in Waiting state
- `queue_record_picking`: Queue in Picking phase
- `queue_record_match_ready`: Queue in Match Ready (game in progress)
- `mock_player_dao`: Mock player data access
- `mock_queue_dao`: Mock queue data access

### `test_queue_manager_pre_queue.py` ⭐ **Core Business Logic Tests**
Tests for QueueManager pre-queue functions (highest priority):

**TestAddPreQueuePlayer** (7 tests)
- ✅ Player successfully joins pre-queue when game is Match Ready
- ✅ Reject join when game in Waiting state
- ✅ Reject join during Picking phase (Match Ready only)
- ✅ Prevent duplicate entries
- ✅ Enforce MAX_QUEUE_SIZE capacity (8 players)
- ✅ Register new players on first join
- ✅ Don't re-register existing players
- ✅ Handle concurrent write failures gracefully

**TestRemovePreQueuePlayer** (3 tests)
- ✅ Player successfully leaves pre-queue
- ✅ Leaving when not in pre-queue is safe (no-op)
- ✅ Handle concurrent write failures

**TestPromotePreQueue** (7 tests) ⭐ **CRITICAL**
- ✅ Promote empty pre-queue
- ✅ Move pre-queue → active queue
- ✅ Respect capacity limit during promotion
- ✅ Clear pre-queue after promotion
- ✅ Maintain join order
- ✅ Don't affect other queue fields
- ✅ Handle full pre-queue (8 players)

**TestPreQueueIntegration** (3 tests)
- ✅ Multiple sequential joins
- ✅ Pre-queue survives `clear_queue()`
- ✅ End-to-end: game finish → promotion flow

### `test_button_manager_pre_queue.py`
Tests for button routing and handlers:

**TestButtonFlowTreeRouting** (4 tests)
- ✅ Route join_pre_queue button
- ✅ Route leave_pre_queue button
- ✅ Pre-queue routes before regular queue (no collision)
- ✅ Other buttons still work (regression)

**TestJoinPreQueueButton** (4 tests)
- ✅ Delegates to QueueManager.add_pre_queue_player
- ✅ Extracts queue_id from custom_id
- ✅ Returns early on failure
- ✅ Updates queue view on success

**TestLeavePreQueueButton** (4 tests)
- ✅ Delegates to QueueManager.remove_pre_queue_player
- ✅ Extracts queue_id correctly
- ✅ Returns early on failure
- ✅ Updates queue view on success

**TestButtonManagerIntegration** (1 test)
- ✅ Join → Leave flow

### `test_queue_dao_pre_queue_model.py`
Tests for data model and persistence:

**TestQueueRecordPreQueueField** (3 tests)
- ✅ Default to empty list
- ✅ Accept provided list
- ✅ Include in `__dict__` for serialization

**TestClearQueuePreservesPreQueue** (3 tests) ⭐ **CRITICAL**
- ✅ Pre-queue survives `clear_queue()`
- ✅ Pre-queue survives with expiry reset
- ✅ Clear empty pre-queue safely

**TestQueueRecordImmutability** (2 tests)
- ✅ Append creates new list
- ✅ Remove creates new list

**TestQueueRecordPreQueueEdgeCases** (4 tests)
- ✅ None defaults to empty
- ✅ Handle large lists (1000+)
- ✅ Tolerates duplicates (business logic dedupes)
- ✅ Isolated from other queue fields

### `test_pre_queue_integration_e2e.py`
End-to-end integration and state machine tests:

**TestGameLifecycleWithPreQueue** (3 tests)
- ✅ Full lifecycle: Waiting → Match Ready → Promotion
- ✅ Cancelled game → promotion
- ✅ Pre-queue overflow during promotion

**TestPreQueueCapacityScenarios** (3 tests)
- ✅ At capacity promotion
- ✅ Join at capacity rejected
- ✅ Partial pre-queue promotion

**TestPreQueueStateIsolation** (2 tests)
- ✅ Pre-queue isolated during Picking
- ✅ Pre-queue not counted in active queue

## Running the Tests

### Install pytest
```bash
pip install pytest pytest-mock
```

### Run all tests
```bash
pytest tests/ -v
```

### Run specific test file
```bash
pytest tests/test_queue_manager_pre_queue.py -v
```

### Run specific test class
```bash
pytest tests/test_queue_manager_pre_queue.py::TestPromotePreQueue -v
```

### Run specific test
```bash
pytest tests/test_queue_manager_pre_queue.py::TestPromotePreQueue::test_promote_pre_queue_to_active_queue -v
```

### Run with coverage
```bash
pytest tests/ --cov=core --cov=dao --cov-report=term-missing
```

## Test Coverage

Target: **80%+ coverage** on pre-queue logic

**Current focus:**
- Core business logic (add/remove/promote) ✅
- Data model persistence ✅
- Button routing ✅
- State transitions ✅
- Edge cases & capacity ✅
- Integration flows ✅

## Key Test Scenarios

### Critical Paths (must pass)
1. **Promotion on game end**: Pre-queue → active queue atomically
2. **Pre-queue survives clear**: `clear_queue()` doesn't wipe waiting room
3. **Capacity enforcement**: Max 8 players in pre-queue
4. **Match Ready only**: Can't join pre-queue in Waiting/Picking states

### Edge Cases Covered
- Empty pre-queue
- Pre-queue at capacity (8)
- Pre-queue overflow (>8, capped)
- Concurrent writes (optimistic lock failures)
- Player re-registration
- Duplicate join attempts
- Cancel vs. win flows

### Integration Scenarios
- Full game lifecycle with pre-queue
- Multiple players joining sequentially
- Join/leave/rejoin flow
- Isolation from picking/game logic
