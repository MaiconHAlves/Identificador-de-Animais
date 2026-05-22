package com.maiconalves.animaldetector

import android.os.Parcel
import android.os.Parcelable

data class DetectionDTO(
    val classId: Int,
    val label: String,
    val confidence: Float,
    val x1: Float,
    val y1: Float,
    val x2: Float,
    val y2: Float,
) : Parcelable {

    constructor(parcel: Parcel) : this(
        parcel.readInt(),
        parcel.readString() ?: "",
        parcel.readFloat(),
        parcel.readFloat(),
        parcel.readFloat(),
        parcel.readFloat(),
        parcel.readFloat(),
    )

    override fun writeToParcel(parcel: Parcel, flags: Int) {
        parcel.writeInt(classId)
        parcel.writeString(label)
        parcel.writeFloat(confidence)
        parcel.writeFloat(x1)
        parcel.writeFloat(y1)
        parcel.writeFloat(x2)
        parcel.writeFloat(y2)
    }

    override fun describeContents() = 0

    companion object CREATOR : Parcelable.Creator<DetectionDTO> {
        override fun createFromParcel(parcel: Parcel) = DetectionDTO(parcel)
        override fun newArray(size: Int) = arrayOfNulls<DetectionDTO>(size)
    }
}
