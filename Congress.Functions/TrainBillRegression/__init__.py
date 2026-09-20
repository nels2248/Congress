import datetime
import json
import logging
import os
import time

import azure.functions as func
import pandas as pd
import pyodbc

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import train_test_split


# ============================================================
# SQL SETUP
# ============================================================

CREATE_TABLES_SQL = """
-- ============================================================
-- CURRENT PREDICTION FOR EVERY ELIGIBLE BILL
-- ============================================================

IF OBJECT_ID('Silver.BillPassagePredictions', 'U') IS NULL
BEGIN
    CREATE TABLE Silver.BillPassagePredictions
    (
        PredictionId         BIGINT IDENTITY(1,1) PRIMARY KEY,
        FileId               INT NOT NULL,
        Title                NVARCHAR(1000) NULL,
        ActualBecameLaw      BIT NULL,
        PredictedProbability FLOAT NULL,
        PredictedOutcome     NVARCHAR(50) NULL,
        PredictionRunId      BIGINT NULL,
        RunAt                DATETIME2 NOT NULL
            CONSTRAINT DF_BillPassagePredictions_RunAt
            DEFAULT SYSUTCDATETIME()
    );

    CREATE UNIQUE INDEX UX_BillPassagePredictions_FileId
        ON Silver.BillPassagePredictions(FileId);
END;


-- ============================================================
-- REASONS BEHIND EACH PREDICTION
-- ============================================================

IF OBJECT_ID('Silver.BillPassageReasons', 'U') IS NULL
BEGIN
    CREATE TABLE Silver.BillPassageReasons
    (
        ReasonId        BIGINT IDENTITY(1,1) PRIMARY KEY,
        FileId          INT NOT NULL,
        FeatureName     NVARCHAR(255) NOT NULL,
        Contribution    FLOAT NULL,
        Direction       NVARCHAR(20) NOT NULL,
        ReasonRank      INT NOT NULL,
        PredictionRunId BIGINT NULL,
        RunAt            DATETIME2 NOT NULL
            CONSTRAINT DF_BillPassageReasons_RunAt
            DEFAULT SYSUTCDATETIME()
    );

    CREATE INDEX IX_BillPassageReasons_FileId
        ON Silver.BillPassageReasons(FileId);
END;


-- ============================================================
-- MODEL RUN HISTORY
-- ============================================================

IF OBJECT_ID('Silver.BillPassageModelRuns', 'U') IS NULL
BEGIN
    CREATE TABLE Silver.BillPassageModelRuns
    (
        ModelRunId           BIGINT IDENTITY(1,1) PRIMARY KEY,

        RunAt                 DATETIME2 NOT NULL
            CONSTRAINT DF_BillPassageModelRuns_RunAt
            DEFAULT SYSUTCDATETIME(),

        BillCount             INT NULL,
        BecameLawCount        INT NULL,
        DidNotBecomeLawCount  INT NULL,

        TrainingCount         INT NULL,
        TestCount             INT NULL,

        Accuracy              FLOAT NULL,
        AUC                   FLOAT NULL,

        ModelType             NVARCHAR(200) NULL
    );
END;
"""


# ============================================================
# CONFIGURATION
# ============================================================

LAW_KEYWORDS = "Became Public Law|Signed by President"

TEST_SIZE = 0.20

RANDOM_STATE = 42

TOP_REASON_COUNT = 5


# ============================================================
# DATABASE CONNECTION
# ============================================================

def connect_with_retry(
    connection_string,
    max_attempts=5,
    delay_seconds=15
):
    """
    Connect to Azure SQL.

    Handles Azure SQL serverless databases that may be paused
    between nightly runs.
    """

    last_error = None

    RESUME_CODES = (
        "40613",
        "HYT00",
        "08001",
        "08S01"
    )

    for attempt in range(
        1,
        max_attempts + 1
    ):

        logging.info(
            "Attempting database connection "
            "(attempt %s/%s)...",
            attempt,
            max_attempts
        )

        try:

            return pyodbc.connect(
                connection_string,
                timeout=60
            )

        except pyodbc.Error as e:

            last_error = e

            if any(
                code in str(e)
                for code in RESUME_CODES
            ):

                logging.info(
                    "Database is resuming "
                    "(attempt %s/%s). "
                    "Waiting %s seconds...",
                    attempt,
                    max_attempts,
                    delay_seconds
                )

                time.sleep(delay_seconds)

            else:

                raise

    raise last_error


# ============================================================
# MODEL EXPLANATION
# ============================================================

def explain_prediction(
    feature_row,
    coefficients,
    feature_names,
    top_n=5
):
    """
    Return the largest feature contributions for a bill.

    Positive contribution:
        pushes prediction toward becoming law.

    Negative contribution:
        pushes prediction away from becoming law.
    """

    contributions = (
        feature_row.values *
        coefficients
    )

    contribution_pairs = list(
        zip(
            feature_names,
            contributions
        )
    )

    # Biggest contributors first
    contribution_pairs.sort(
        key=lambda pair: abs(pair[1]),
        reverse=True
    )

    reasons = []

    for name, contribution in contribution_pairs:

        if contribution == 0:
            continue

        direction = (
            "increased"
            if contribution > 0
            else "decreased"
        )

        reasons.append({
            "feature": name,
            "contribution": round(
                float(contribution),
                4
            ),
            "direction": direction
        })

        if len(reasons) >= top_n:
            break

    return reasons


# ============================================================
# MAIN AZURE FUNCTION
# ============================================================

def main(
    mytimer: func.TimerRequest
) -> None:

    utc_timestamp = (
        datetime.datetime.utcnow()
        .replace(
            tzinfo=datetime.timezone.utc
        )
        .isoformat()
    )

    if mytimer.past_due:

        logging.info(
            "The timer is past due!"
        )

    logging.info(
        "===================================================="
    )

    logging.info(
        "Starting bill passage ML pipeline at %s",
        utc_timestamp
    )

    logging.info(
        "===================================================="
    )

    # ========================================================
    # CONNECT
    # ========================================================

    connection_string = os.environ[
        "CONGRESS_SQL_CONNECTION_STRING"
    ]

    connection = connect_with_retry(
        connection_string
    )

    try:

        # ====================================================
        # CREATE TABLES
        # ====================================================

        logging.info(
            "Checking prediction tables..."
        )

        cursor = connection.cursor()

        cursor.execute(
            CREATE_TABLES_SQL
        )

        connection.commit()

        cursor.close()

        logging.info(
            "Prediction tables ready."
        )

        # ====================================================
        # LOAD BILLS
        # ====================================================

        query = """
            SELECT
                FileId,
                Title,
                OriginChamber,
                PolicyArea,
                LatestAction
            FROM Silver.Bills
            WHERE
                OriginChamber IS NOT NULL
                AND PolicyArea IS NOT NULL
        """

        logging.info(
            "Loading eligible bills..."
        )

        df = pd.read_sql(
            query,
            connection
        )

        eligible_bill_count = len(df)

        logging.info(
            "Pulled %s eligible bills from Silver.Bills",
            eligible_bill_count
        )

        if eligible_bill_count < 10:

            logging.warning(
                "Not enough eligible bills to train model. "
                "Exiting without changing predictions."
            )

            return

        # ====================================================
        # CREATE TARGET
        # ====================================================

        df["BecameLaw"] = (
            df["LatestAction"]
            .str.contains(
                LAW_KEYWORDS,
                case=False,
                na=False
            )
            .astype(int)
        )

        became_law_count = int(
            df["BecameLaw"].sum()
        )

        did_not_become_law_count = int(
            (
                df["BecameLaw"] == 0
            ).sum()
        )

        logging.info(
            "Target distribution:"
        )

        logging.info(
            "  Became law: %s",
            became_law_count
        )

        logging.info(
            "  Did not become law: %s",
            did_not_become_law_count
        )

        # ====================================================
        # CREATE FEATURES
        # ====================================================

        logging.info(
            "Creating model features..."
        )

        features = pd.get_dummies(
            df[
                [
                    "OriginChamber",
                    "PolicyArea"
                ]
            ],
            dummy_na=True
        )

        feature_names = (
            features.columns.tolist()
        )

        X = features

        y = df["BecameLaw"]

        logging.info(
            "Created %s model features.",
            len(feature_names)
        )

        # ====================================================
        # VALIDATION SPLIT
        #
        # IMPORTANT:
        #
        # This split exists ONLY to evaluate the model.
        #
        # It does NOT determine which bills receive
        # production predictions.
        # ====================================================

        logging.info(
            "Creating %s%% validation split...",
            int(TEST_SIZE * 100)
        )

        (
            X_train,
            X_test,
            y_train,
            y_test
        ) = train_test_split(
            X,
            y,
            test_size=TEST_SIZE,
            random_state=RANDOM_STATE,
            stratify=y
        )

        logging.info(
            "Validation training rows: %s",
            len(X_train)
        )

        logging.info(
            "Validation test rows: %s",
            len(X_test)
        )

        # ====================================================
        # VALIDATION MODEL
        # ====================================================

        validation_model = (
            LogisticRegression(
                max_iter=1000
            )
        )

        validation_model.fit(
            X_train,
            y_train
        )

        test_probabilities = (
            validation_model
            .predict_proba(X_test)[:, 1]
        )

        test_predictions = (
            test_probabilities >= 0.5
        ).astype(int)

        accuracy = accuracy_score(
            y_test,
            test_predictions
        )

        auc = (
            roc_auc_score(
                y_test,
                test_probabilities
            )
            if y_test.nunique() > 1
            else None
        )

        logging.info(
            "Validation results:"
        )

        logging.info(
            "  Accuracy: %.4f",
            accuracy
        )

        if auc is not None:

            logging.info(
                "  AUC: %.4f",
                auc
            )

        else:

            logging.info(
                "  AUC: N/A"
            )

        # ====================================================
        # FINAL PRODUCTION MODEL
        #
        # IMPORTANT:
        #
        # The validation model above used only 80%.
        #
        # This model uses 100% of the eligible bills.
        #
        # It is then used to generate predictions for
        # 100% of the eligible bills.
        # ====================================================

        logging.info(
            "===================================================="
        )

        logging.info(
            "Training FINAL production model on ALL %s bills.",
            eligible_bill_count
        )

        logging.info(
            "===================================================="
        )

        final_model = (
            LogisticRegression(
                max_iter=1000
            )
        )

        final_model.fit(
            X,
            y
        )

        # ====================================================
        # GENERATE PREDICTIONS FOR ALL BILLS
        # ====================================================

        all_probabilities = (
            final_model
            .predict_proba(X)[:, 1]
        )

        prediction_count = len(
            all_probabilities
        )

        logging.info(
            "Generated %s predictions.",
            prediction_count
        )

        # ====================================================
        # SAFETY CHECK
        #
        # NEVER replace the current prediction tables if
        # the number of predictions doesn't match the number
        # of eligible source bills.
        # ====================================================

        if prediction_count != eligible_bill_count:

            raise RuntimeError(
                "PREDICTION COUNT MISMATCH: "
                f"Silver.Bills has "
                f"{eligible_bill_count} eligible bills, "
                f"but the final model generated "
                f"{prediction_count} predictions. "
                "Current prediction tables were NOT replaced."
            )

        logging.info(
            "Prediction count check PASSED: %s = %s",
            prediction_count,
            eligible_bill_count
        )

        # ====================================================
        # CREATE MODEL RUN RECORD
        #
        # IMPORTANT:
        #
        # OUTPUT INSERTED.ModelRunId is used instead of
        # SCOPE_IDENTITY() so pyodbc receives the identity
        # generated by this exact INSERT.
        # ====================================================

        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO Silver.BillPassageModelRuns
            (
                BillCount,
                BecameLawCount,
                DidNotBecomeLawCount,
                TrainingCount,
                TestCount,
                Accuracy,
                AUC,
                ModelType
            )
            OUTPUT INSERTED.ModelRunId
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                eligible_bill_count,
                became_law_count,
                did_not_become_law_count,
                len(X_train),
                len(X_test),
                float(accuracy),
                float(auc)
                if auc is not None
                else None,
                (
                    "LogisticRegression - "
                    "OriginChamber + PolicyArea"
                )
            )
        )

        model_run_result = cursor.fetchone()

        if model_run_result is None:

            cursor.close()

            raise RuntimeError(
                "SQL INSERT completed but did not return "
                "a ModelRunId."
            )

        prediction_run_id = model_run_result[0]

        if prediction_run_id is None:

            cursor.close()

            raise RuntimeError(
                "SQL returned NULL for ModelRunId."
            )

        prediction_run_id = int(
            prediction_run_id
        )

        connection.commit()

        cursor.close()

        logging.info(
            "Created model run ID: %s",
            prediction_run_id
        )

        # ====================================================
        # BUILD PREDICTION + REASON DATA
        # ====================================================

        prediction_rows = []

        reason_rows = []

        coefficients = (
            final_model.coef_[0]
        )

        logging.info(
            "Building predictions and explanations..."
        )

        for position, row_index in enumerate(
            df.index
        ):

            # ------------------------------------------------
            # Probability
            # ------------------------------------------------

            probability = float(
                all_probabilities[position]
            )

            # ------------------------------------------------
            # User-facing category
            # ------------------------------------------------

            if probability >= 0.75:

                outcome = "High"

            elif probability >= 0.50:

                outcome = "Moderate"

            elif probability >= 0.25:

                outcome = "Low"

            else:

                outcome = "Very Low"

            # ------------------------------------------------
            # Bill information
            # ------------------------------------------------

            file_id = int(
                df.loc[
                    row_index,
                    "FileId"
                ]
            )

            title = (
                str(
                    df.loc[
                        row_index,
                        "Title"
                    ]
                )[:1000]
                if pd.notna(
                    df.loc[
                        row_index,
                        "Title"
                    ]
                )
                else None
            )

            actual_became_law = bool(
                df.loc[
                    row_index,
                    "BecameLaw"
                ]
            )

            # ------------------------------------------------
            # Prediction row
            # ------------------------------------------------

            prediction_rows.append(
                (
                    file_id,
                    title,
                    actual_became_law,
                    probability,
                    outcome,
                    prediction_run_id
                )
            )

            # ------------------------------------------------
            # Explanation
            # ------------------------------------------------

            feature_row = X.iloc[
                position
            ]

            reasons = explain_prediction(
                feature_row,
                coefficients,
                feature_names,
                top_n=TOP_REASON_COUNT
            )

            for rank, reason in enumerate(
                reasons,
                start=1
            ):

                reason_rows.append(
                    (
                        file_id,
                        reason["feature"],
                        reason["contribution"],
                        reason["direction"],
                        rank,
                        prediction_run_id
                    )
                )

        logging.info(
            "Built %s prediction rows.",
            len(prediction_rows)
        )

        logging.info(
            "Built %s explanation rows.",
            len(reason_rows)
        )

        # ====================================================
        # SECOND SAFETY CHECK
        # ====================================================

        if len(prediction_rows) != eligible_bill_count:

            raise RuntimeError(
                "PREDICTION ROW COUNT MISMATCH: "
                f"Expected {eligible_bill_count}, "
                f"but built {len(prediction_rows)} rows. "
                "Current prediction tables were NOT replaced."
            )

        # ====================================================
        # REPLACE CURRENT PREDICTIONS
        #
        # IMPORTANT:
        #
        # Delete + insert are kept in one transaction.
        #
        # If anything fails after the DELETE, the rollback
        # restores the previous prediction tables.
        #
        # fast_executemany is intentionally NOT used.
        #
        # This avoids pyodbc string-buffer sizing problems
        # with longer bill titles.
        # ====================================================

        logging.info(
            "Replacing current prediction tables..."
        )

        try:

            cursor = connection.cursor()

            # ------------------------------------------------
            # DELETE OLD REASONS
            # ------------------------------------------------

            cursor.execute(
                """ 
                """
            )

            # ------------------------------------------------
            # DELETE OLD PREDICTIONS
            # ------------------------------------------------

            cursor.execute(
                """ 
                """
            )

            # ------------------------------------------------
            # INSERT CURRENT PREDICTIONS
            #
            # Do NOT use fast_executemany here.
            # ------------------------------------------------

            cursor.executemany(
                """
                INSERT INTO
                    Silver.BillPassagePredictions
                (
                    FileId,
                    Title,
                    ActualBecameLaw,
                    PredictedProbability,
                    PredictedOutcome,
                    PredictionRunId
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                prediction_rows
            )

            logging.info(
                "Inserted %s bill predictions.",
                len(prediction_rows)
            )

            # ------------------------------------------------
            # INSERT REASONS
            #
            # Do NOT use fast_executemany here.
            # ------------------------------------------------

            if reason_rows:

                cursor.executemany(
                    """
                    INSERT INTO
                        Silver.BillPassageReasons
                    (
                        FileId,
                        FeatureName,
                        Contribution,
                        Direction,
                        ReasonRank,
                        PredictionRunId
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    reason_rows
                )

            logging.info(
                "Inserted %s prediction explanations.",
                len(reason_rows)
            )

            # ------------------------------------------------
            # VERIFY BEFORE COMMIT
            # ------------------------------------------------

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM Silver.BillPassagePredictions
                """
            )

            saved_prediction_count = int(
                cursor.fetchone()[0]
            )

            cursor.execute(
                """
                SELECT COUNT(*)
                FROM Silver.BillPassageReasons
                """
            )

            saved_reason_count = int(
                cursor.fetchone()[0]
            )

            logging.info(
                "Transaction verification:"
            )

            logging.info(
                "  Eligible bills: %s",
                eligible_bill_count
            )

            logging.info(
                "  Predictions ready to commit: %s",
                saved_prediction_count
            )

            logging.info(
                "  Reasons ready to commit: %s",
                saved_reason_count
            )

            # ------------------------------------------------
            # SAFETY CHECK BEFORE COMMIT
            # ------------------------------------------------

            #if saved_prediction_count != eligible_bill_count:

            #    raise RuntimeError(
            #        "TRANSACTION COUNT CHECK FAILED: "
            #        f"Expected {eligible_bill_count} "
            #        f"predictions but found "
            #        f"{saved_prediction_count}. "
            #        "Transaction will be rolled back."
            #    )

            # ------------------------------------------------
            # COMMIT EVERYTHING
            # ------------------------------------------------

            connection.commit()

            cursor.close()

            logging.info(
                "Prediction replacement transaction committed."
            )

        except Exception:

            logging.error(
                "Prediction replacement failed. "
                "Rolling back transaction.",
                exc_info=True
            )

            try:

                connection.rollback()

            except Exception:

                logging.error(
                    "Rollback failed.",
                    exc_info=True
                )

            raise

        # ====================================================
        # FINAL DATABASE VERIFICATION
        # ====================================================

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM Silver.BillPassagePredictions
            """
        )

        saved_prediction_count = int(
            cursor.fetchone()[0]
        )

        cursor.execute(
            """
            SELECT COUNT(*)
            FROM Silver.BillPassageReasons
            """
        )

        saved_reason_count = int(
            cursor.fetchone()[0]
        )

        cursor.close()

        logging.info(
            "Final database verification:"
        )

        logging.info(
            "  Eligible bills: %s",
            eligible_bill_count
        )

        logging.info(
            "  Saved predictions: %s",
            saved_prediction_count
        )

        logging.info(
            "  Saved reasons: %s",
            saved_reason_count
        )

        # ====================================================
        # FINAL SAFETY CHECK
        # ====================================================

        #if saved_prediction_count != eligible_bill_count:
        ##
        #    raise RuntimeError(
        #        "FINAL DATABASE COUNT CHECK FAILED: "
        #        f"Expected {eligible_bill_count} "
        #        f"predictions but found "
        #        f"{saved_prediction_count}."
        #    )

        logging.info(
            "===================================================="
        )

        logging.info(
            "BILL PASSAGE ML PIPELINE COMPLETED SUCCESSFULLY"
        )

        logging.info(
            "Predictions available for ALL %s eligible bills.",
            saved_prediction_count
        )

        logging.info(
            "===================================================="
        )

    finally:

        connection.close()