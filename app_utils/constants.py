STORE_CHOICES = [('use', 'Store'), ('debt', 'Debt'), ('online', 'Online')]
AMOUNT_TYPES = [('in', 'Inflow'), ('out', 'Outflow')]
SALARY_TYPES = [('ns', 'Net Salary'), ('gs', 'Gross Salary')]
MEMBER_ACCESS_LEVELS = [(1, 'Member Admin'), (2, 'Staff Admin'), (3, 'Member')]
BUDGET_STATUSES = [('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved')]

EMAIL_MSGS = [
	"It seems you have not earned or spent any money for the whole [type], Uuhhm! Is that odd to you? If you have "
	"forgot to record those transactions, you may have them somewhere or in your mind.",
	"Looks like there’s no record of earnings or spending this [type], hmm! Does that seem odd? If you forgot to log "
	"anything, maybe you still have it in mind.",
	"It appears there’s no financial activity for the [type]. Could that be right? If you missed recording something, "
	"it might still be fresh in your mind.",
	"No money in or out this [type]. Does that seem strange to you? You might have forgotten to log a transaction—try "
	"recalling it!",
	"You haven’t recorded any transactions this [type]. Is that unusual? If something slipped by, perhaps you can "
	"remember it now.",
	"It’s been a quiet [type] on your account. Could that be a mistake? If you forgot to record something, you may still "
	"have it in mind.",
	"Nothing earned or spent this [type]—does that feel odd? If something slipped your memory, you may still recall those "
	"transactions.",
	"Hmm, no financial activity this [type]. Does that stand out? If you forgot to track anything, you may have it stored "
	"somewhere or in your mind.",
	"It looks like your wallet has stayed closed this [type]. Is that odd? If you’ve missed logging anything, now’s a "
	"good time to think back.",
	"Your account has been still this [type]. Does that surprise you? If something wasn’t recorded, you may still have it "
	"in mind.",
	"There’s no record of spending or earning this [type]. Does that seem right? If you missed tracking a transaction, "
	"it might still be in your memory.",
	"You’ve got no transactions this [type]—anything seem strange about that? If you forgot to log them, they might still "
	"be fresh in your mind.",
	"It seems your account has been untouched this [type]. Does that feel odd? If you didn’t record something, perhaps "
	"you can recall it.",
	"No earnings or expenses recorded this [type]. Could that be a mistake? If you’ve missed logging any, they could "
	"still be in your mind.",
	"It’s been a zero-transaction [type]—does that catch your attention? If something was missed, maybe you can still "
	"think back and recall it.",
	"It seems there’s no movement in your account this [type]. Is that strange to you? If anything went unrecorded, "
	"it might still be in your memory.",
	"A [type] without earnings or spending—does that surprise you? You may have missed logging a transaction, but it "
	"could still be on your mind.",
	"It looks like no money was moved this [type]—does that stand out? If you forgot to track something, perhaps you "
	"still remember it.",
	"No income or expenses for the [type]—anything odd about that? If something was missed, you might still be able to "
	"recall it.",
	"Your account has seen no activity this [type]—does that seem off to you? If something slipped your memory, "
	"it could still be somewhere in your mind.",
	"It looks like no transactions were recorded this [type]. Does that seem unusual? You may have forgotten to log "
	"something—try thinking back.",
	"It seems there’s no financial movement this [type]. Does that feel right to you? If something wasn’t logged, "
	"you may still remember it.",
	"Your account has been quiet this [type]—does that surprise you? If you forgot to track anything, it might still be "
	"fresh in your mind.",
	"There are no transactions logged for this [type]—does that seem strange? If something was missed, you might still "
	"have it in your memory.",
	"It looks like your finances stayed still this [type]. Is that odd? You may have forgotten to record something—try "
	"recalling it.",
	"No income or spending recorded this [type]—anything stand out? If you forgot to track something, you might still "
	"remember it.",
	"It seems there was no financial activity this [type]. Does that surprise you? If you forgot to log any transactions, "
	"you may still have them in mind.",
	"Your account has seen no changes this [type]—does that seem unusual? If anything was missed, it might still be fresh "
	"in your memory.",
	"It seems like no transactions were made this [type]. Does that feel odd? If you’ve forgotten to record something, "
	"you may still have it in your mind.",
	"It looks like your account has been quiet this [type]—anything odd about that? If you missed tracking a transaction, "
	"you may still remember it.",
	"No earnings or expenses for the whole [type]—does that feel right? If you missed recording anything, perhaps you can "
	"recall it now. "
]
