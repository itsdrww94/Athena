/**
 * Athena Finance Algorithm - Safe-to-Spend Logic
 * This module is designed to be used in n8n Code nodes
 * 
 * The algorithm determines if a purchase is financially safe based on:
 * 1. Current balance
 * 2. Proposed purchase price
 * 3. Safety buffer (default $2000)
 * 4. Upcoming bills consideration
 */

// ============================================================================
// MAIN SAFE-TO-SPEND FUNCTION
// ============================================================================

/**
 * Determines if a purchase is safe to make
 * @param {number} currentBalance - Current account balance
 * @param {number} purchasePrice - Price of the item to buy
 * @param {number} safetyBuffer - Minimum amount to keep in account (default: 2000)
 * @param {number} upcomingBills - Sum of bills due in next 7 days (default: 0)
 * @returns {object} Decision object with approval status and details
 */
function canSpend(currentBalance, purchasePrice, safetyBuffer = 2000, upcomingBills = 0) {
    const availableBalance = currentBalance - safetyBuffer - upcomingBills;
    const canAfford = availableBalance >= purchasePrice;
    const remainingAfterPurchase = availableBalance - purchasePrice;
    
    // Calculate risk level
    let riskLevel = 'LOW';
    if (remainingAfterPurchase < 500) {
        riskLevel = 'HIGH';
    } else if (remainingAfterPurchase < 1000) {
        riskLevel = 'MEDIUM';
    }
    
    return {
        approved: canAfford,
        riskLevel: riskLevel,
        currentBalance: currentBalance,
        purchasePrice: purchasePrice,
        safetyBuffer: safetyBuffer,
        upcomingBills: upcomingBills,
        availableToSpend: Math.max(0, availableBalance),
        remainingAfterPurchase: canAfford ? remainingAfterPurchase : null,
        message: canAfford 
            ? `✅ Purchase approved. You'll have $${remainingAfterPurchase.toFixed(2)} available after this purchase.`
            : `❌ Purchase not recommended. You need $${(purchasePrice - availableBalance).toFixed(2)} more to safely afford this.`
    };
}

// ============================================================================
// SPENDING ANALYSIS FUNCTIONS
// ============================================================================

/**
 * Analyzes spending patterns from transaction history
 * @param {Array} transactions - Array of transaction objects
 * @returns {object} Spending analysis
 */
function analyzeSpending(transactions) {
    const categoryTotals = {};
    let totalSpent = 0;
    
    transactions.forEach(t => {
        if (t.transaction_type === 'expense') {
            categoryTotals[t.category] = (categoryTotals[t.category] || 0) + parseFloat(t.amount);
            totalSpent += parseFloat(t.amount);
        }
    });
    
    // Sort categories by spending
    const sortedCategories = Object.entries(categoryTotals)
        .sort((a, b) => b[1] - a[1])
        .map(([category, amount]) => ({
            category,
            amount,
            percentage: ((amount / totalSpent) * 100).toFixed(1)
        }));
    
    return {
        totalSpent,
        categoryBreakdown: sortedCategories,
        topCategory: sortedCategories[0]?.category || 'None',
        transactionCount: transactions.length
    };
}

/**
 * Calculates daily spending allowance based on remaining budget
 * @param {number} monthlyBudget - Total monthly budget
 * @param {number} spentSoFar - Amount spent this month
 * @param {number} daysRemaining - Days left in the month
 * @returns {object} Daily allowance info
 */
function getDailyAllowance(monthlyBudget, spentSoFar, daysRemaining) {
    const remaining = monthlyBudget - spentSoFar;
    const dailyAllowance = remaining / Math.max(1, daysRemaining);
    
    return {
        remaining,
        daysRemaining,
        dailyAllowance: Math.max(0, dailyAllowance),
        onTrack: spentSoFar <= (monthlyBudget * ((30 - daysRemaining) / 30)),
        message: dailyAllowance > 0 
            ? `💰 You can spend $${dailyAllowance.toFixed(2)} per day for the rest of the month.`
            : `⚠️ You've exceeded your budget by $${Math.abs(remaining).toFixed(2)}.`
    };
}

// ============================================================================
// N8N INTEGRATION
// For use in n8n Code nodes, export the input item with the result
// ============================================================================

// Example n8n usage:
// const result = canSpend($input.item.json.balance, $input.item.json.price);
// return { json: result };

module.exports = {
    canSpend,
    analyzeSpending,
    getDailyAllowance
};
