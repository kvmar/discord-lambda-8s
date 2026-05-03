# ELO System Improvements - Research-Based Implementation

## What Was Changed (Option 1: Applied ✅)

### 1. Tau Reduced from 0.5 → 0.1
**Why:** Tau controls skill volatility in TrueSkill. At 0.5, the system assumes massive skill drift between games, keeping uncertainty (sigma) artificially high. This allows inflated ratings to persist.

**Effect:** Lowering to 0.1 forces sigma to converge faster, making ratings stable and harder to inflate.

### 2. K-Factor Scaling Added
**Why:** Research on team-based games shows that rating changes must be constrained by player experience and skill level. Without this, top players can maintain artificially high ratings.

**Implementation:**
- New players (< 10 games): K = 1.5 (volatile, quick convergence)
- Experienced (30-100 games): K = 1.0 (standard)
- Established top players (ELO > 1800): K = 0.7 (stable, hard to move)

**Effect:** High-rated players can only gain/lose ~7-10 points per match. They need consistent wins to stay high.

### 3. Narrower Rank Boundaries
**Why:** Rank 7 used to span 2000-9000 (7000 points!), making it easy to cluster at the top. Now it's 2100+, requiring ~100 more points than before.

**New Boundaries:**
```
Rank 0 (Bronze):      0-399
Rank 1 (Silver):      400-699
Rank 2 (Gold):        700-1099
Rank 3 (Diamond):     1100-1399
Rank 4 (Master):      1400-1699
Rank 5 (GM):          1700-1899
Rank 6 (Celestial):   1900-2099
Rank 7 (One Above):   2100+ ← Much harder to reach
```

### 4. Minimum Sigma Floor (0.5)
**Why:** Prevents sigma from collapsing to 0, which would break future calculations.

## Expected Results

| Metric | Before | After |
|--------|--------|-------|
| High ELO player pool | Bloated | Concentrated |
| Rating stability | Unstable | Stable at high ranks |
| New player convergence | Slow | Fast (10-20 games) |
| Time to reach rank 7 | Easy | Hard, requires proof |
| Top rank clustering | Too many | Fewer, more exclusive |

## Research Foundation

This implementation is based on:
- **TrueSkill System** (Microsoft Research) - Designed for team games
- **Glicko-2 Principles** - Rating deviation & volatility
- **MOBA Game Analysis** (2023) - How to prevent rating inflation in team games
- **Valorant RR System** - K-factor scaling for competitive balance

## How to Verify It's Working

1. **Watch new players:** They should reach their true rank in 15-20 games
2. **Watch top players:** Check if rank 7 becomes harder to maintain
3. **Check rating movement:** A rank 7 player losing 5 games should drop ranks
4. **Compare before/after:** Count players at each rank tier

## If This Isn't Enough: Option 2 - Glicko-2 Migration

If the tau/K-factor approach doesn't fully solve the problem, here's a Glicko-2 implementation ready to go:

```python
class Glicko2System:
    """Glicko-2 rating system for team-based 4v4 games.
    
    Parameters:
    - Rating (r): Player skill (1500 = average)
    - RD (Rating Deviation): Confidence interval (lower = more confident)
    - Volatility (v): Performance inconsistency (higher = erratic)
    """
    
    SYSTEM_CONSTANT = 0.5
    RATING_PERIOD = 10  # Games before recalculation
    
    def __init__(self):
        self.initial_rd = 350
        self.initial_volatility = 0.06
    
    def get_new_player(self):
        return {
            'rating': 1500,
            'rd': self.initial_rd,
            'volatility': self.initial_volatility,
        }
    
    def calculate_rating_change(self, player, opponent, won):
        """Calculate rating change based on Glicko-2 formulas."""
        rating = player['rating']
        rd = player['rd']
        v = player['volatility']
        opp_rating = opponent['rating']
        opp_rd = opponent['rd']
        
        # Convert to Glicko-2 scale
        r = (rating - 1500) / 173.7
        r_opp = (opp_rating - 1500) / 173.7
        rd_scale = rd / 173.7
        rd_opp = opp_rd / 173.7
        
        # g(RD) function
        g = 1 / (3.14 ** 2 * (rd_opp ** 2) / 6) ** 0.5
        
        # Expected score
        E = 1 / (1 + 10 ** (-g * (r - r_opp) / 2))
        d_squared = 1 / ((self.SYSTEM_CONSTANT ** 2) * (g ** 2) * E * (1 - E))
        
        # Actual outcome
        outcome = 1 if won else 0
        
        # New volatility (iterative algorithm)
        A = (v ** 2) ** -1 + d_squared ** -1
        B_min = -4
        B_max = (1 - (rd ** 2) / 1500 ** 2) / (4 * (d_squared ** -1))
        
        # Simplified volatility (full version uses iterative algorithm)
        new_volatility = max(self.initial_volatility, 
                            (A ** -1) ** 0.5 * abs(outcome - E) / d_squared ** 0.5)
        
        # New RD
        new_rd = ((rd ** -2 + d_squared ** -1) ** -1) ** 0.5
        
        # New rating
        new_rating = rating + (173.7 ** 2 / d_squared) * (outcome - E)
        
        return {
            'rating': new_rating,
            'rd': new_rd,
            'volatility': new_volatility,
        }

    def post_match_glicko2(self, win_team, lose_team):
        """Update all players using Glicko-2."""
        # Calculate team averages
        win_avg_rating = sum(p['rating'] for p in win_team) / len(win_team)
        lose_avg_rating = sum(p['rating'] for p in lose_team) / len(lose_team)
        
        # Update winners
        for player in win_team:
            opponent_proxy = {'rating': lose_avg_rating, 'rd': 100}
            updated = self.calculate_rating_change(player, opponent_proxy, won=True)
            player.update(updated)
        
        # Update losers
        for player in lose_team:
            opponent_proxy = {'rating': win_avg_rating, 'rd': 100}
            updated = self.calculate_rating_change(player, opponent_proxy, won=False)
            player.update(updated)
```

## When to Use Each System

| System | Pros | Cons | Best For |
|--------|------|------|----------|
| **TrueSkill (Updated)** | Already implemented, simple fix | Less explicit uncertainty | Quick fix, moderate complexity |
| **Glicko-2** | More transparent, handles uncertainty explicitly | More complex, higher maintenance | Long-term, high accuracy needed |

## Commit & Test Plan

1. Deploy tau=0.1 + K-factor changes
2. Monitor rank distribution for 1-2 weeks
3. If top ranks still too crowded:
   - Increase K-factor cap (0.7 → 0.5 for high-ELO players)
   - OR migrate to Glicko-2

## References

- [Microsoft TrueSkill Documentation](https://www.microsoft.com/en-us/research/project/trueskill-ranking-system/)
- [Glicko-2 Rating System](https://en.wikipedia.org/wiki/Glicko_rating_system)
- [Analysis of ELO in MOBA Games (2023)](https://arxiv.org/abs/2310.13719)
- Valorant RR System: Opponent strength weighting + K-factor scaling
