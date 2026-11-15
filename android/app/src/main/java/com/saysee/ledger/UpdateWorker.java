package com.saysee.ledger;

import android.content.Context;

import androidx.annotation.NonNull;
import androidx.work.Worker;
import androidx.work.WorkerParameters;

import org.json.JSONObject;

/** Runs about twice a day in the background: looks for a new version and sends one notification; on the 1st, says last month's report is ready. */
public class UpdateWorker extends Worker {
    public UpdateWorker(@NonNull Context c, @NonNull WorkerParameters p) { super(c, p); }

    @NonNull
    @Override
    public Result doWork() {
        JSONObject u = UpdateChecker.check(getApplicationContext());
        UpdateChecker.notifyOnce(getApplicationContext(), u);
        UpdateChecker.monthReport(getApplicationContext());
        return Result.success();
    }
}
